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
    Create a timeline visualization of robot events using matplotlib.
    
    Args:
        data: Processed data dictionary containing messages
        selected_topics: List of topics to display
        current_time: Current playback time
        height: Height of the visualization
        
    Returns:
        Streamlit matplotlib figure
    """
    if not data:
        st.warning("No data available for visualization")
        return None
    
    # Check if we have traditional messages format
    if "messages" in data and data["messages"]:
        events = []
        
        # Process from ROS Bridge messages
        for msg in data["messages"]:
            if "topic" in msg and (selected_topics is None or msg["topic"] in selected_topics):
                if "msg" in msg and isinstance(msg["msg"], dict):
                    event = {}
                    
                    # Extract timestamp
                    if "header" in msg["msg"] and "stamp" in msg["msg"]["header"]:
                        stamp = msg["msg"]["header"]["stamp"]
                        ts = float(stamp["secs"]) + float(stamp["nsecs"]) / 1e9
                        event["header"] = {"stamp": {"secs": ts}}
                    
                    # Extract event type
                    if "target" in msg["msg"] and "event" in msg["msg"]["target"]:
                        event["event"] = msg["msg"]["target"]["event"]
                    
                    # Extract capability
                    if "source" in msg["msg"] and "capability" in msg["msg"]["source"]:
                        event["source"] = {"capability": msg["msg"]["source"]["capability"]}
                    
                    # Extract topic
                    event["topic"] = msg["topic"]
                    
                    # Add to events list if we have enough data
                    if "header" in event and "source" in event:
                        events.append(event)
        
        data["events"] = events
    
    # Return if we don't have any events
    if "events" not in data or not data["events"]:
        st.warning("No event data available.")
        return None
    
    # Filter events by selected topics
    filtered_events = data["events"]
    if selected_topics:
        filtered_events = [e for e in data["events"] if e.get("topic") in selected_topics]
    
    if not filtered_events:
        st.info("No matching events for selected topics.")
        return None
    
    # Create the figure
    fig, ax = plt.subplots(figsize=(12, height/100), facecolor='#1e1e1e')
    ax.set_facecolor('#1e1e1e')  # Dark background for the plot area
    
    # Define colors for event types
    colors = {
        0: "#3498db",  # Info (Blue)
        1: "#2ecc71",  # Start (Green)
        2: "#e74c3c",  # End (Red) 
        3: "#f39c12",  # Error (Orange)
        4: "#9b59b6"   # Success (Purple)
    }
    
    # Event type names for legend
    legend = {
        0: "Info",
        1: "Start",
        2: "End",
        3: "Error",
        4: "Success"
    }
    
    # Store labels for y-axis
    y_labels = []
    y_positions = []
    
    # Plot events
    for idx, event in enumerate(filtered_events):
        # Extract event data
        stamp = event.get("header", {}).get("stamp", {}).get("secs", 0)
        capability = event.get("source", {}).get("capability", "Unknown")
        event_type = event.get("event", 0)
        
        # Use a horizontal bar to represent event
        ax.barh(idx, 0.8, left=stamp, height=0.6, 
                color=colors.get(event_type, "gray"), 
                alpha=0.8, edgecolor='white', linewidth=0.5)
        
        # Store label information
        y_labels.append(capability.split('/')[-1] if '/' in capability else capability)  # Show only last part of capability name
        y_positions.append(idx)
    
    # Set y-axis ticks and labels
    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=9, color='white')
    
    # Set labels and title with white color for dark theme
    ax.set_xlabel("Time (secs)", color='white', fontsize=10)
    ax.set_title("Robot Event Timeline", color='white', fontsize=14, pad=10)
    
    # Set grid for better readability
    ax.grid(True, linestyle='--', alpha=0.3, color='gray')
    
    # Style the axes for dark theme
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white') 
    ax.spines['right'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    
    # Add legend
    patches = [mpatches.Patch(color=color, label=legend[code]) 
               for code, color in colors.items() if code in [e.get("event", 0) for e in filtered_events]]
    ax.legend(handles=patches, loc='upper right', framealpha=0.7, 
              facecolor='#1e1e1e', edgecolor='white', fontsize=9, labelcolor='white')
    
    # Highlight current time if provided
    if current_time is not None:
        ax.axvline(current_time, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.text(current_time, len(filtered_events) * 0.95, "Current", 
                color='red', fontsize=9, ha='right', va='top',
                bbox=dict(facecolor='#1e1e1e', alpha=0.7, edgecolor='red', boxstyle='round'))
    
    plt.tight_layout()
    return fig

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
    from pyvis.network import Network
    import networkx as nx
    import streamlit.components.v1 as components
    import time
    
    if "node_paths" not in data or not data["node_paths"]:
        st.info("No node path data available for visualization")
        return None
    
    node_paths = data["node_paths"]
    capability_count = node_paths.get("capability_count", 0)
    
    # Display the count of capabilities found
    st.info(f"Found {capability_count} unique capabilities in the robot data")
    
    # Create a NetworkX directed graph
    G = nx.DiGraph()
    
    # Create a mapping of capability nodes
    capability_nodes = {}
    message_nodes = {}
    
    # Process nodes first to identify capabilities
    if "nodes" in node_paths and node_paths["nodes"]:
        for node in node_paths["nodes"]:
            node_id = node.get("id", "")
            node_name = node.get("name", "")
            is_capability = node.get("is_capability", False)
            
            if is_capability and node_name:
                # For capabilities, clean up the name to just show the last part
                if "/" in node_name:
                    display_name = node_name.split("/")[-1]
                else:
                    display_name = node_name
                
                # Store mapping for easy lookup
                capability_nodes[node_id] = {"name": node_name, "display_name": display_name}
                
                # Add to graph
                G.add_node(node_name, title=node_name, group=1)
            elif node_id.startswith("message_"):
                # For message nodes, create a cleaner display name
                display_name = node_name
                if len(display_name) > 30:
                    display_name = f"{display_name[:27]}..."
                
                message_nodes[node_id] = {"name": node_name, "display_name": display_name}
                
                # Add to graph
                G.add_node(node_name, title=node_name, group=2)
    
    # Process connections to draw edges
    if "connections" in node_paths and node_paths["connections"]:
        for conn in node_paths["connections"]:
            source_id = conn.get("source")
            target_id = conn.get("target")
            topic = conn.get("topic", "")
            timestamp = conn.get("timestamp", 0)
            event_type = conn.get("event", 0)
            text = conn.get("text", "")
            
            # Map event types to names
            event_names = {
                0: "Info",
                1: "Start",
                2: "End",
                3: "Error",
                4: "Success"
            }
            event_name = event_names.get(event_type, "Unknown")
            
            # Get node information
            source_info = None
            target_info = None
            
            if source_id in capability_nodes:
                source_info = capability_nodes[source_id]
            elif source_id in message_nodes:
                source_info = message_nodes[source_id]
                
            if target_id in capability_nodes:
                target_info = capability_nodes[target_id]
            elif target_id in message_nodes:
                target_info = message_nodes[target_id]
            
            # Skip if we don't have valid source and target
            if not source_info or not target_info:
                continue
                
            source_name = source_info["name"]
            target_name = target_info["name"]
            
            # Create a meaningful edge label
            edge_label = f"{event_name}"
            if topic:
                topic_short = topic.split('/')[-1]
                edge_label += f" - {topic_short}"
            if timestamp:
                edge_label += f" ({timestamp:.2f}s)"
                
            # Add edge to graph
            G.add_edge(source_name, target_name, 
                       title=edge_label, 
                       label=event_name,
                       color=get_event_color(event_type),
                       time=timestamp)
    
    # Show dropdowns in Streamlit for shortest path
    st.markdown("### Shortest Path Highlighter")
    
    # Get all capability nodes for dropdown
    all_nodes = sorted(list(G.nodes()))
    
    # Select nodes for shortest path highlighting
    col1, col2 = st.columns(2)
    with col1:
        start_node = st.selectbox("Select Start Node", all_nodes, key="start_node")
    with col2:
        end_node = st.selectbox("Select End Node", all_nodes, key="end_node")
        
    # Calculate shortest path
    shortest_path = []
    try:
        if start_node and end_node and start_node != end_node:
            shortest_path = nx.shortest_path(G, source=start_node, target=end_node)
            st.success(f"Found path with {len(shortest_path)-1} steps between nodes")
    except nx.NetworkXNoPath:
        st.warning(f"No path exists between {start_node} and {end_node}")
    except Exception as e:
        st.error(f"Error finding path: {str(e)}")
    
    # Create PyVis network with dark background color (#36393e)
    net = Network(height=f"{height}px", width="100%", directed=True, notebook=False, bgcolor="#36393e", font_color="white")
    
    # Set physics options for better layout
    net.set_options("""
    {
      "physics": {
        "hierarchicalRepulsion": {
          "centralGravity": 0.0,
          "springLength": 150,
          "springConstant": 0.01,
          "nodeDistance": 200,
          "damping": 0.09
        },
        "solver": "hierarchicalRepulsion",
        "stabilization": {
          "iterations": 100
        }
      },
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "LR",
          "sortMethod": "directed",
          "levelSeparation": 250
        }
      },
      "interaction": {
        "navigationButtons": true,
        "keyboard": true
      },
      "configure": {
        "enabled": false
      },
      "nodes": {
        "font": {
          "color": "#ffffff"
        }
      },
      "edges": {
        "font": {
          "color": "#ffffff"
        }
      }
    }
    """)
    
    # Import from NetworkX
    net.from_nx(G)
    
    # Customize nodes based on type and shortest path
    for node in net.nodes:
        node_id = node["id"]
        
        # Check if this node is a capability
        is_capability = any(info["name"] == node_id for info in capability_nodes.values())
        
        # Set node properties based on type with lighter font color for dark background
        if is_capability:
            node["color"] = "#e74c3c"  # Red for capabilities
            node["size"] = 25
            node["font"] = {"size": 14, "color": "white"}
            node["borderWidth"] = 2
            
            # Highlight CapabilityGetRunner specifically
            if "CapabilityGetRunner" in node_id:
                node["color"] = "#9b59b6"  # Purple
                node["borderWidth"] = 3
                node["borderWidthSelected"] = 5
                node["size"] = 30
        else:
            node["color"] = "#3498db"  # Blue for messages
            node["size"] = 20
            node["font"] = {"size": 12, "color": "white"}
        
        # Highlight nodes in the shortest path
        if shortest_path and node_id in shortest_path:
            node["borderWidth"] = 2
            node["borderWidthSelected"] = 4
            if is_capability:
                node["color"] = "#2ecc71"  # Green
            else:
                node["color"] = "#27ae60"  # Darker green
            node["size"] += 5
    
    # Highlight edges in the shortest path
    for edge in net.edges:
        if shortest_path:
            if edge["from"] in shortest_path and edge["to"] in shortest_path:
                from_index = shortest_path.index(edge["from"])
                to_index = shortest_path.index(edge["to"])
                if to_index == from_index + 1:  # Consecutive nodes in path
                    edge["width"] = 5
                    edge["color"] = "#2ecc71"  # Green
                    edge["arrows"] = {"to": {"enabled": True, "scaleFactor": 1.5}}
    
    # Generate unique path for the HTML file
    path = f"/tmp/graph_{time.time()}.html"
    net.save_graph(path)
    
    # Read the HTML file and display it with Streamlit
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Display the interactive graph
    components.html(html, height=height)
    
    # Show if CapabilityGetRunner was found
    capability_runner_found = any("CapabilityGetRunner" in node for node in G.nodes())
    st.info(f"CapabilityGetRunner Status: {'Found' if capability_runner_found else 'Not Found'}")
    
    # Add explanation of the visualization
    with st.expander("Understanding the Node Path Visualization"):
        st.markdown("""
        ### How to Interact with the Graph
        
        This interactive network visualization shows connections between robot capabilities and messages:
        
        - **Red Nodes**: Capability nodes (robot functions)
        - **Blue Nodes**: Message nodes (status updates, event messages)
        - **Purple Node**: CapabilityGetRunner (special capability)
        - **Lines**: Connections between nodes with their event types
        - **Direction**: Arrows show the flow of information
        
        You can:
        - **Zoom**: Use the mouse wheel or pinch gestures
        - **Pan**: Click and drag to move around
        - **Select**: Click on nodes to highlight their connections
        - **Find Path**: Use the dropdowns above to highlight the shortest path between nodes
        """)
    
    return None

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
