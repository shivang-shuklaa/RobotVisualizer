from pyvis.network import Network
import networkx as nx
import streamlit as st
import streamlit.components.v1 as components
import time
import json

def create_node_path_visualization(data, current_time=None, height=600):
    """
    Create an interactive visualization of the robot thinking pattern through node paths using PyVis.
    
    Args:
        data: Processed data dictionary containing node path information
        current_time: Current playback time
        height: Height of the visualization
        
    Returns:
        None - Renders the interactive network directly in Streamlit
    """
    # Create a NetworkX directed graph
    G = nx.DiGraph()

    # Add nodes and edges from the event data
    for entry in data.get("events", []):
        source = entry.get("source", {}).get("capability")
        target = entry.get("target", {}).get("capability")
        label = entry.get("text", "")

        if source and target:
            G.add_node(source)
            G.add_node(target)
            G.add_edge(source, target, label=label)

    if G.number_of_nodes() == 0:
        st.warning("No valid node path data found in the file.")
        return None

    # Toggle to show all paths from all nodes
    show_all_paths = st.checkbox("Show All Paths from All Nodes")

    if show_all_paths:
        st.markdown("### All Directed Paths in Graph")
        for start_node in G.nodes():
            for end_node in G.nodes():
                if start_node != end_node:
                    try:
                        path = nx.shortest_path(G, source=start_node, target=end_node)
                        st.markdown(f"`{start_node}` → `{end_node}`: {' → '.join(path)}")
                    except:
                        continue
        return None

    # Show dropdowns in Streamlit for shortest path
    st.markdown("### Shortest Path Highlighter")
    all_nodes = list(G.nodes())
    start_node = st.selectbox("Select Start Node", all_nodes, key="start_node")
    end_node = st.selectbox("Select End Node", all_nodes, key="end_node")

    try:
        shortest_path = nx.shortest_path(G, source=start_node, target=end_node)
    except Exception:
        st.error(f"No path exists between {start_node} and {end_node}")
        shortest_path = []

    # Create a subgraph if a path exists
    subgraph_nodes = shortest_path if shortest_path else []
    subgraph_edges = [(shortest_path[i], shortest_path[i+1]) for i in range(len(shortest_path)-1)] if shortest_path else []
    SG = nx.DiGraph()
    SG.add_nodes_from(subgraph_nodes)
    SG.add_edges_from(subgraph_edges)

    # Create PyVis network
    net = Network(height=f"{height}px", directed=True, bgcolor="#0e1117", font_color="white")
    net.from_nx(SG if shortest_path else G)

    # Highlight shortest path nodes and edges
    for node in net.nodes:
        if node["id"] in shortest_path:
            node["color"] = "lightgreen"
            node["size"] = 20

    for edge in net.edges:
        if edge["from"] in shortest_path and edge["to"] in shortest_path:
            from_index = shortest_path.index(edge["from"])
            to_index = shortest_path.index(edge["to"])
            if to_index == from_index + 1:
                edge["color"] = "red"
                edge["width"] = 3

    # Force-directed layout
    net.repulsion(node_distance=200, central_gravity=0.3, spring_length=200, damping=0.9)

    # Save to HTML and show in Streamlit
    path = f"/tmp/graph_{time.time()}.html"
    net.show(path)
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    components.html(html, height=height)

    # Display available paths from the selected start node
    st.markdown("### All Reachable End Nodes from Selected Start Node")
    reachable = list(nx.descendants(G, start_node))
    if reachable:
        for target in reachable:
            try:
                path = nx.shortest_path(G, source=start_node, target=target)
                st.markdown(f"`{start_node}` → `{target}`: {' → '.join(path)}")
            except:
                continue
    else:
        st.info(f"No reachable nodes from `{start_node}`.")
        
    return None

def create_json_viewer(data, selected_topics=None, current_time=None, height=600):
    """
    Display the uploaded JSON data in a Streamlit JSON viewer.
    
    Args:
        data: Processed data dictionary containing messages
        selected_topics: List of topics to display
        current_time: Current playback time
        height: Height of the visualization
        
    Returns:
        None - Displays JSON data directly in Streamlit
    """
    st.subheader("Uploaded JSON Data Viewer")
    st.json(data)
    return None

def get_available_topics(data):
    """
    Extract available topics from the processed data.
    
    Args:
        data: Processed robot data
        
    Returns:
        list: Available topics for visualization
    """
    topics = set()
    
    # Get topics from events
    for entry in data.get("events", []):
        if "topic" in entry:
            topics.add(entry["topic"])
            
    # Get topics from messages
    for msg in data.get("messages", []):
        if "topic" in msg:
            topics.add(msg["topic"])
    
    # Get topics from metadata
    if "topic_metadata" in data:
        topics.update(data["topic_metadata"].keys())
    
    # Get topics from time series data
    if "time_series" in data:
        topics.update(data["time_series"].keys())
    
    # Remove duplicates and sort
    return sorted(list(topics))