import streamlit as st
import pandas as pd
import json
import numpy as np
import os
import uuid
import time
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import networkx as nx
import streamlit.components.v1 as components

def create_event_timeline(data, selected_topics=None, current_time=None, height=600):
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
    
    # Check if we have data
    if not data:
        st.warning("No data available for viewing")
        return None
    
    # Display the JSON data for easy inspection
    try:
        # Filter by topics if specified
        if selected_topics and "messages" in data:
            filtered_data = {
                "messages": [
                    msg for msg in data.get("messages", [])
                    if "topic" in msg and msg["topic"] in selected_topics
                ]
            }
            if filtered_data["messages"]:
                st.json(filtered_data)
            else:
                st.info("No messages match the selected topics")
                st.json(data)  # Show all data as fallback
        else:
            # Show all data
            st.json(data)
    except Exception as e:
        st.error(f"Error displaying JSON data: {str(e)}")
    
    return None

def get_layout_config(selected_topics=None):
    """
    Generate a layout configuration for Foxglove based on selected topics.
    
    Args:
        selected_topics: List of topics to include in the layout
        
    Returns:
        dict: Layout configuration
    """
    # Default layout optimized for ROS bridge capabilities messages
    layout = {
        "direction": "row",
        "first": {
            "direction": "column",
            "first": {
                "activePanel": {
                    "title": "3D",
                    "type": "3D"
                }
            },
            "second": {
                "direction": "row",
                "first": {
                    "activePanel": {
                        "title": "Raw Messages",
                        "type": "RawMessages",
                        "config": {
                            "topicPath": "/capabilities/events"
                        }
                    }
                },
                "second": {
                    "activePanel": {
                        "title": "State Transitions",
                        "type": "StateTransitions",
                        "config": {
                            "paths": {
                                "timestamp": "header.stamp",
                                "state": "target.event"
                            }
                        }
                    }
                },
                "splitPercentage": 50
            },
            "splitPercentage": 60
        },
        "second": {
            "direction": "column",
            "first": {
                "activePanel": {
                    "title": "Plot",
                    "type": "Plot",
                    "config": {
                        "paths": [
                            {
                                "value": "target.event",
                                "enabled": True,
                                "timestampMethod": "header.stamp"
                            },
                            {
                                "value": "target.thread_id",
                                "enabled": True,
                                "timestampMethod": "header.stamp"
                            }
                        ]
                    }
                }
            },
            "second": {
                "activePanel": {
                    "title": "Table",
                    "type": "Table",
                    "config": {
                        "topicPath": "/capabilities/events"
                    }
                }
            },
            "splitPercentage": 50
        },
        "splitPercentage": 60
    }
    
    # Customize layout based on selected topics
    if selected_topics:
        has_capabilities = any("/capabilities" in topic for topic in selected_topics)
        
        # If capabilities topics are not selected, use a more generic layout
        if not has_capabilities:
            layout = {
                "direction": "row",
                "first": {
                    "direction": "column",
                    "first": {
                        "activePanel": {
                            "title": "3D",
                            "type": "3D"
                        }
                    },
                    "second": {
                        "activePanel": {
                            "title": "Raw Messages",
                            "type": "RawMessages"
                        }
                    },
                    "splitPercentage": 70
                },
                "second": {
                    "direction": "column",
                    "first": {
                        "activePanel": {
                            "title": "Plot",
                            "type": "Plot"
                        }
                    },
                    "second": {
                        "activePanel": {
                            "title": "Table",
                            "type": "Table"
                        }
                    },
                    "splitPercentage": 50
                },
                "splitPercentage": 60
            }
    
    return layout

def get_available_topics(data):
    """
    Extract available topics from the processed data.
    
    Args:
        data: Processed robot data
        
    Returns:
        list: Available topics for visualization
    """
    topics = []
    
    # Get topics from metadata
    if "topic_metadata" in data:
        topics.extend(data["topic_metadata"].keys())
    
    # Get topics from time series data
    if "time_series" in data:
        topics.extend(data["time_series"].keys())
    
    # Remove duplicates and sort
    topics = sorted(list(set(topics)))
    
    return topics

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
    topics = set()
    for entry in data.get("events", []):
        topic = entry.get("topic")
        if topic:
            topics.add(topic)
    return list(topics)

def create_node_path_visualization(data, current_time=None, height=600):
    """
    Create an interactive visualization of the robot thinking pattern through node paths using PyVis.
    
    Args:
        data: Processed data dictionary containing node path information
        current_time: Current playback time
        height: Height of the visualization
        
    Returns:
        True if visualization was created, False otherwise
    """
    from pyvis.network import Network
    import networkx as nx
    import streamlit.components.v1 as components
    import time
    import json
    
    # Create a NetworkX directed graph
    G = nx.DiGraph()
    valid_connections = 0

    # Add nodes and edges from the event data
    for entry in data.get("events", []):
        # Fallback capability extraction
        source = entry.get("source", {}).get("capability") or entry.get("source", {}).get("label")
        target = entry.get("target", {}).get("capability") or entry.get("target", {}).get("label")
        label = entry.get("text", "")

        # Clean up whitespace and type-check
        if isinstance(source, str):
            source = source.strip()
        else:
            source = None
        if isinstance(target, str):
            target = target.strip()
        else:
            target = None

        if source and target:
            G.add_node(source)
            G.add_node(target)
            G.add_edge(source, target, label=label)
            valid_connections += 1

    if valid_connections == 0:
        st.warning("No valid node path data found in the file.")
        st.markdown("#### Debugging: Preview of first 5 event entries with source/target")
        for i, entry in enumerate(data.get("events", [])[:5]):
            st.write(f"Event {i+1}")
            st.json({
                "source": entry.get("source", {}),
                "target": entry.get("target", {}),
                "text": entry.get("text", "")
            })
        return False

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
        return True

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

    return True

def get_event_color(event_type):
    """Helper function to get color for event type"""
    event_colors = {
        0: "#3498db",  # Info (Blue)
        1: "#2ecc71",  # Start (Green)
        2: "#e74c3c",  # End (Red)
        3: "#f39c12",  # Error (Orange)
        4: "#9b59b6"   # Success (Purple)
    }
    return event_colors.get(event_type, "#7f7f7f")

def update_foxglove_state(iframe_id, current_time, selected_topics=None, playback_speed=1.0):
    """
    Generate JavaScript to update the Foxglove iframe state.
    
    Args:
        iframe_id: ID of the iframe element
        current_time: Current playback time
        selected_topics: List of topics to display
        playback_speed: Playback speed
        
    Returns:
        str: JavaScript code to update the iframe
    """
    # This would be used for dynamic updating of the Foxglove state
    # However, Streamlit's ability to inject JavaScript is limited
    # This is for future implementation if Streamlit adds more JavaScript support
    js_code = f"""
    const iframe = document.getElementById('{iframe_id}');
    const message = {{
        type: 'foxglove.seek',
        time: {current_time},
        speed: {playback_speed}
    }};
    
    if (iframe && iframe.contentWindow) {{
        iframe.contentWindow.postMessage(message, '*');
    }}
    """
    
    return js_code
