import streamlit as st
import json
import networkx as nx
from pyvis.network import Network
from streamlit.components.v1 import html
import pandas as pd
import altair as alt
import plotly.graph_objs as go

# Optional: for auto‑play
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st.warning("Install 'streamlit-autorefresh' for auto‑play functionality.")

# ----------------------------------------------------------------------------
# CACHING FUNCTIONS
# ----------------------------------------------------------------------------

@st.cache_data
def load_data(uploader):
    return json.load(uploader)

@st.cache_data
def parse_robot_data(data):
    events, poses, joints = [], [], []
    for msg in data:
        ts = msg.get('timestamp') or msg.get('header', {}).get('stamp', {})
        if isinstance(ts, dict):
            ts = ts.get('secs', 0) + ts.get('nsecs', 0) * 1e-9
        try:
            ts = float(ts)
        except:
            continue
        op = msg.get('operation', 'message')
        topic = msg.get('topic', '')
        content = msg.get('msg') or msg.get('data') or {}

        src = content.get('from') or content.get('source')
        dst = content.get('to') or content.get('target')
        evt = content.get('type') or op
        if src and dst:
            events.append({'timestamp': ts, 'topic': topic, 'type': evt,
                           'source': src, 'target': dst, 'raw': content})

        pos = content.get('position')
        if isinstance(pos, dict):
            poses.append({'timestamp': ts, 'x': pos.get('x'),
                          'y': pos.get('y'), 'z': pos.get('z')})

        js = content.get('joint_states')
        if isinstance(js, dict):
            for name, angle in js.items():
                joints.append({'timestamp': ts, 'joint': name, 'angle': angle})

    df_e = (pd.DataFrame(events)
            .dropna(subset=['source', 'target'])
            .sort_values('timestamp')
            .reset_index(drop=True))
    df_p = pd.DataFrame(poses).sort_values('timestamp').reset_index(drop=True) if poses else pd.DataFrame()
    df_j = pd.DataFrame(joints).sort_values('timestamp').reset_index(drop=True) if joints else pd.DataFrame()
    return df_e, df_p, df_j

# ----------------------------------------------------------------------------
# APP SETUP
# ----------------------------------------------------------------------------

st.set_page_config(page_title="Advanced Robot Path Dashboard", layout="wide")
st.sidebar.title("🤖 Robot Path Visualization")

uploaded = st.sidebar.file_uploader("Upload JSON file", type=["json"])
if not uploaded:
    st.info(
        """
        **Upload a JSON file to begin.**

        Features:
        - Interactive Node Path Visualization (force/hierarchical/circular)
        - JSON Raw & Table Explorer with CSV export
        - Playback: Play/Pause/Reset/Slider/Auto‑play
        - Filters: topic, type, time window, node search, edge weight
        - Node Inspector & Shortest‑Path Finder
        - GraphML Export
        - Analytics: Heatmap, Sankey, Centrality, Time‑Series
        - Pose & Joint Visualizations (3D scatter & timelines)
        - Custom colors, theme, physics toggle
        """
    )
    st.stop()

data = load_data(uploaded)
df_events, df_poses, df_joints = parse_robot_data(data)
if df_events.empty:
    st.error("No valid event messages in JSON.")
    st.stop()

t_min, t_max = df_events['timestamp'].min(), df_events['timestamp'].max()

# ----------------------------------------------------------------------------
# SIDEBAR CONTROLS
# ----------------------------------------------------------------------------

st.sidebar.header("Filters & Controls")
topics = sorted(df_events['topic'].unique())
types  = sorted(df_events['type'].unique())

sel_topics  = st.sidebar.multiselect("Topics", topics, default=topics)
sel_types   = st.sidebar.multiselect("Event Types", types, default=types)
time_window = st.sidebar.slider("Time Window (s)",
                                float(t_min), float(t_max),
                                (float(t_min), float(t_max)),
                                step=1.0)
search_node = st.sidebar.text_input("Search Node")

edges_all = df_events.groupby(['source','target']).size().reset_index(name='weight')
max_w     = int(edges_all['weight'].max())
thresh    = st.sidebar.slider("Min Edge Weight", 1, max(1,max_w), 1)

type_colors = {
    t: st.sidebar.color_picker(f"Color for {t}",
                               f"#{(i*50)%256:02x}{(i*80)%256:02x}{(i*110)%256:02x}")
    for i,t in enumerate(types)
}
theme         = st.sidebar.selectbox("Theme", ['light','dark'])
enable_physics= st.sidebar.checkbox("Enable Physics", False)
layout_opt    = st.sidebar.selectbox("Layout", ['force','hierarchical','circular'])
auto_play     = st.sidebar.checkbox("Auto‑play", False)
play_speed    = st.sidebar.slider("Play Speed (s/tick)", 0.1, 5.0, 1.0, step=0.1)

if st.sidebar.button("Reset Filters"):
    sel_topics, sel_types, time_window, search_node = topics, types, (t_min, t_max), ''

# ----------------------------------------------------------------------------
# PLAYBACK STATE
# ----------------------------------------------------------------------------

if 'current_time' not in st.session_state:
    st.session_state.current_time = t_min
if 'playing' not in st.session_state:
    st.session_state.playing = False

c1, c2, c3 = st.sidebar.columns(3)
if c1.button("▶ Play"):   st.session_state.playing = True
if c2.button("⏸ Pause"):  st.session_state.playing = False
if c3.button("🔁 Reset"):  st.session_state.current_time = t_min

# run autorefresh only when playing or auto_play
if st.session_state.playing or auto_play:
    try:
        st_autorefresh(interval=int(play_speed*1000), limit=None, key="auto_ref")
        st.session_state.current_time = min(t_max, st.session_state.current_time + play_speed)
    except:
        pass

st.session_state.current_time = st.sidebar.slider("Current Time (s)",
                                                 float(t_min), float(t_max),
                                                 st.session_state.current_time,
                                                 step=1.0)
cur_time = st.session_state.current_time

# ----------------------------------------------------------------------------
# FILTERED DATA & GRAPH
# ----------------------------------------------------------------------------

df_f = df_events[
    (df_events.timestamp >= time_window[0]) &
    (df_events.timestamp <= cur_time) &
    df_events.topic.isin(sel_topics) &
    df_events.type.isin(sel_types)
]
if search_node:
    mask = df_f.source.str.contains(search_node, case=False) | df_f.target.str.contains(search_node, case=False)
    df_f = df_f[mask]

if df_f.empty:
    st.warning("No events match current filters.")
edges_df = df_f.groupby(['source','target']).size().reset_index(name='weight')
edges_df = edges_df[edges_df['weight'] >= thresh]

G = nx.DiGraph()
for _, r in edges_df.iterrows():
    sub = df_f[(df_f.source==r.source)&(df_f.target==r.target)]
    evt = sub.type.mode().iloc[0]
    G.add_edge(r.source, r.target,
               weight=int(r.weight),
               color=type_colors.get(evt,'#888888'),
               title=f"Count: {r.weight}")
for n in set(df_f.source)|set(df_f.target):
    if n not in G:
        G.add_node(n)

# community detection
try:
    from networkx.algorithms.community import greedy_modularity_communities
    comms = list(greedy_modularity_communities(G, cutoff=0.05))
    if not comms: comms = [set(G.nodes())]
except:
    comms = [set(G.nodes())]
node_comm = {n:i for i,c in enumerate(comms) for n in c}

# metrics & centralities with safe defaults
if G.number_of_nodes() > 0:
    try:
        density = nx.density(G)
    except:
        density = 0.0
    try:
        clust = nx.average_clustering(G.to_undirected())
    except ZeroDivisionError:
        clust = 0.0
    try:
        avg_short = (nx.average_shortest_path_length(G.to_undirected())
                     if nx.is_connected(G.to_undirected()) else None)
    except:
        avg_short = None
    deg_c   = nx.degree_centrality(G)
    betw_c  = nx.betweenness_centrality(G)
    clos_c  = nx.closeness_centrality(G)
    clustcoef = nx.clustering(G.to_undirected())
    try:
        eig_c = nx.eigenvector_centrality_numpy(G)
    except:
        eig_c = {n:0 for n in G.nodes()}
else:
    density = clust = 0.0
    avg_short = None
    deg_c = betw_c = clos_c = clustcoef = {}
    eig_c = {}

# ----------------------------------------------------------------------------
# TABS UI
# ----------------------------------------------------------------------------

tabs = st.tabs(["Overview","Visualization","Inspector","Data","Analytics","Pose/Joint"])

with tabs[0]:
    st.header("Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Events", len(df_events))
    c1.metric("Filtered Events", len(df_f))
    c2.metric("Unique Nodes", G.number_of_nodes())
    c2.metric("Communities", len(comms))
    c3.metric("Density", f"{density:.3f}")
    c3.metric("Avg Clustering", f"{clust:.3f}")
    if avg_short is not None:
        c3.metric("Avg Shortest Path", f"{avg_short:.3f}")

with tabs[1]:
    st.header("Network Visualization")
    if G.number_of_nodes()==0:
        st.info("No nodes to display.")
    else:
        net = Network(height="650px", width="100%", directed=True,
                      bgcolor="#222222" if theme=="dark" else "#FFFFFF",
                      font_color="#FFFFFF" if theme=="dark" else "#000000")
        if not enable_physics:
            try: net.toggle_physics(False)
            except: pass
        if layout_opt=="hierarchical":
            net.set_options(json.dumps({
                "layout":{"hierarchical":{"enabled":True,"direction":"UD","sortMethod":"directed"}}
            }))
        elif layout_opt=="circular":
            pos = nx.circular_layout(G, scale=500)
        for n in G.nodes():
            idx = node_comm.get(n,-1)
            col = f"#{(idx*40)%256:02x}{(idx*80)%256:02x}aa" if idx>=0 else "#888888"
            if layout_opt=="circular":
                x,y = pos[n]; net.add_node(n, label=n, color=col, x=x, y=y, fixed=True)
            else:
                net.add_node(n, label=n, color=col)
        for u,v,d in G.edges(data=True):
            net.add_edge(u,v,color=d["color"],width=d["weight"]*0.5,title=d["title"])
        try: net.show_buttons(filter_=['physics'])
        except: pass
        html(net.generate_html(), height=650)
        st.download_button("Download GraphML", "\n".join(nx.generate_graphml(G)), file_name="graph.graphml")

with tabs[2]:
    st.header("Inspector & Shortest Path")
    if G.number_of_nodes()==0:
        st.info("No nodes to inspect.")
    else:
        nodes = sorted(G.nodes())
        sel_n = st.selectbox("Select Node", nodes)
        if sel_n:
            st.metric("Degree",    G.degree(sel_n))
            st.metric("In‑Degree", G.in_degree(sel_n))
            st.metric("Out‑Degree",G.out_degree(sel_n))
            st.metric("Community", node_comm.get(sel_n,-1))
            st.write("Neighbors:", list(G.neighbors(sel_n)))
        st.subheader("Shortest Path")
        src = st.selectbox("From", nodes, key="spf_src")
        dst = st.selectbox("To",   nodes, key="spf_dst")
        if st.button("Find Path"):
            try: st.success(" → ".join(nx.shortest_path(G,src,dst)))
            except: st.error("No path found.")

with tabs[3]:
    st.header("Data Explorer")
    with st.expander("Raw JSON"): st.json(data)
    st.dataframe(df_f.drop(columns=['raw'], errors='ignore'))
    st.download_button("Download CSV", df_f.to_csv(index=False).encode(), file_name="events.csv")

with tabs[4]:
    st.header("Analytics")
    if edges_df.empty:
        st.info("No edges to analyze.")
    else:
        st.subheader("Transition Heatmap")
        heat = alt.Chart(edges_df).mark_rect().encode(
            x='source:N', y='target:N', color='weight:Q'
        )
        st.altair_chart(heat, use_container_width=True)

        st.subheader("Sankey Diagram")
        nlist = list(G.nodes())
        si = [nlist.index(u) for u in edges_df['source']]
        ti = [nlist.index(v) for v in edges_df['target']]
        sankey = go.Figure(go.Sankey(
            node=dict(label=nlist, pad=15, thickness=20),
            link=dict(source=si, target=ti, value=edges_df['weight'])
        ))
        st.plotly_chart(sankey, use_container_width=True)

        st.subheader("Centrality Rankings")
        cent = pd.DataFrame({
            'node': list(G.nodes()),
            'degree': pd.Series(deg_c),
            'betweenness': pd.Series(betw_c),
            'closeness': pd.Series(clos_c),
            'eigenvector': pd.Series(eig_c),
            'clustering_coef': pd.Series(clustcoef)
        }).fillna(0)
        st.table(cent.sort_values('degree', ascending=False).head(5))

        st.subheader("Events Over Time by Topic")
        ts_t = (df_events[df_events.topic.isin(sel_topics)]
                .groupby([pd.cut(df_events['timestamp'], bins=50), 'topic'])
                .size().reset_index(name='count'))
        st.altair_chart(alt.Chart(ts_t).mark_line().encode(
            x='timestamp:O', y='count:Q', color='topic:N'
        ), use_container_width=True)

        st.subheader("Events Over Time by Type")
        ts_ty = (df_events[df_events.type.isin(sel_types)]
                 .groupby([pd.cut(df_events['timestamp'], bins=50), 'type'])
                 .size().reset_index(name='count'))
        st.altair_chart(alt.Chart(ts_ty).mark_line().encode(
            x='timestamp:O', y='count:Q', color='type:N'
        ), use_container_width=True)

with tabs[5]:
    st.header("Pose & Joint States")
    if not df_poses.empty:
        fig3d = go.Figure(go.Scatter3d(
            x=df_poses['x'], y=df_poses['y'], z=df_poses['z'],
            mode='markers+lines', marker=dict(size=3)
        ))
        fig3d.update_layout(scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'))
        st.plotly_chart(fig3d, use_container_width=True)
    else:
        st.info("No pose data.")

    if not df_joints.empty:
        jt = alt.Chart(df_joints).mark_line().encode(
            x='timestamp:Q', y='angle:Q', color='joint:N'
        )
        st.altair_chart(jt, use_container_width=True)
    else:
        st.info("No joint-state data.")
