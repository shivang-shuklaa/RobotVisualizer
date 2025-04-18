import streamlit as st
import pandas as pd
import json
import numpy as np
import os
import uuid
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.dates as mdates
from datetime import datetime, timedelta

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
    if "messages" not in data or not data["messages"]:
        st.info("No message data available for visualization")
        return None
    
    messages = data["messages"]
    
    # Extract timestamps and events
    timestamps = []
    event_types = []
    capabilities = []
    texts = []
    
    for msg in messages:
        if "topic" in msg and (selected_topics is None or msg["topic"] in selected_topics):
            if "msg" in msg and "header" in msg["msg"] and "stamp" in msg["msg"]["header"]:
                # Extract timestamp
                stamp = msg["msg"]["header"]["stamp"]
                ts = float(stamp["secs"]) + float(stamp["nsecs"]) / 1e9
                timestamps.append(ts)
                
                # Extract event type
                event_type = 0
                if "target" in msg["msg"] and "event" in msg["msg"]["target"]:
                    event_type = msg["msg"]["target"]["event"]
                event_types.append(event_type)
                
                # Extract capability
                capability = ""
                if "source" in msg["msg"] and "capability" in msg["msg"]["source"]:
                    capability = msg["msg"]["source"]["capability"]
                capabilities.append(capability)
                
                # Extract message text
                text = ""
                if "target" in msg["msg"] and "text" in msg["msg"]["target"]:
                    text = msg["msg"]["target"]["text"]
                texts.append(text)
    
    if not timestamps:
        st.info("No timeline data available for the selected topics")
        return None
    
    # Create a DataFrame for the events
    df = pd.DataFrame({
        'timestamp': timestamps,
        'event_type': event_types,
        'capability': capabilities,
        'text': texts
    })
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Convert timestamps to datetime for plotting
    min_time = df['timestamp'].min()
    df['datetime'] = [datetime.fromtimestamp(ts) for ts in df['timestamp']]
    
    # Map event types to names and colors
    event_map = {
        0: ("Info", "#1f77b4"),  # Blue
        1: ("Start", "#2ca02c"),  # Green
        2: ("End", "#d62728"),    # Red
        3: ("Error", "#ff7f0e"),  # Orange
        4: ("Success", "#9467bd") # Purple
    }
    
    # Extract unique capabilities and assign colors
    unique_capabilities = df['capability'].unique()
    capability_colors = {}
    
    # Generate a color map for capabilities
    cmap = plt.cm.get_cmap('tab20', len(unique_capabilities))
    
    for i, cap in enumerate(unique_capabilities):
        capability_colors[cap] = cmap(i)
    
    # Create the timeline plot
    fig, ax = plt.subplots(figsize=(10, height/80))
    
    # Plot events as scatter points
    for i, row in df.iterrows():
        event_type = row['event_type']
        event_name, event_color = event_map.get(event_type, ("Unknown", "#7f7f7f"))
        
        capability = row['capability']
        cap_color = capability_colors.get(capability, (0.5, 0.5, 0.5, 1.0))
        
        # Plot point
        ax.scatter(row['datetime'], i, color=event_color, s=80, zorder=3)
        
        # Add capability bar
        if capability:
            ax.hlines(i, row['datetime'] - timedelta(seconds=0.2), 
                     row['datetime'] + timedelta(seconds=0.2), 
                     color=cap_color, linewidth=8, alpha=0.6, zorder=2)
    
    # Add text labels for some points
    for i, row in df.iterrows():
        if i % 3 == 0:  # Only label every 3rd point to avoid overcrowding
            ax.text(row['datetime'], i, f" {row['text'][:15]}...", 
                   fontsize=8, verticalalignment='center')
    
    # Highlight current time if provided
    if current_time is not None:
        current_dt = datetime.fromtimestamp(current_time)
        ax.axvline(current_dt, color='red', linestyle='--', linewidth=2)
    
    # Format the plot
    ax.set_title("Robot Event Timeline")
    ax.set_xlabel("Time")
    ax.set_yticks([])
    
    # Format the x-axis with appropriate time units
    time_range = df['timestamp'].max() - df['timestamp'].min()
    if time_range < 60:  # Less than a minute
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S.%f'))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    
    # Create legend for event types
    legend_elements = []
    for event_type, (name, color) in event_map.items():
        if event_type in df['event_type'].values:
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                            markerfacecolor=color, markersize=10, label=name))
    
    # Add the legend
    ax.legend(handles=legend_elements, loc='upper right')
    
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
    Create a visualization of the robot thinking pattern through node paths.
    
    Args:
        data: Processed data dictionary containing node path information
        current_time: Current playback time
        height: Height of the visualization
        
    Returns:
        Streamlit matplotlib figure
    """
    if "node_paths" not in data or not data["node_paths"]:
        st.info("No node path data available for visualization")
        return None
    
    node_paths = data["node_paths"]
    
    # Check if we have nodes and connections
    if "nodes" not in node_paths or "connections" not in node_paths:
        st.info("Node path data is incomplete")
        return None
    
    nodes = node_paths["nodes"]
    connections = node_paths["connections"]
    
    if not nodes or not connections:
        st.info("No nodes or connections found in the data")
        return None
    
    # Create a larger figure for better readability
    fig, ax = plt.subplots(figsize=(12, height/60))
    
    # Create a dictionary to map node IDs to positions
    node_positions = {}
    
    # Create a dictionary to hold all node data by ID for easy lookup
    node_data_by_id = {node["id"]: node for node in nodes if "id" in node}
    
    # Map node types to colors with more distinctive colors
    node_type_colors = {
        "source": "#00a651",  # Brighter Green for source nodes
        "target": "#0078d7",  # Brighter Blue for target nodes
    }
    
    # Map event types to colors for connections with more vibrant colors
    event_colors = {
        0: "#3498db",  # Info (Blue)
        1: "#2ecc71",  # Start (Green)
        2: "#e74c3c",  # End (Red)
        3: "#f39c12",  # Error (Orange)
        4: "#9b59b6"   # Success (Purple)
    }
    
    # Sort connections by timestamp
    sorted_connections = sorted(connections, key=lambda x: x.get("timestamp", 0))
    
    # Set up vertical positioning for timeline
    timeline_height = len(sorted_connections)
    
    # Collect unique source and target nodes
    unique_source_nodes = set()
    unique_target_nodes = set()
    
    for conn in sorted_connections:
        source_id = conn.get("source")
        target_id = conn.get("target")
        if source_id:
            unique_source_nodes.add(source_id)
        if target_id:
            unique_target_nodes.add(target_id)
            
    # First draw connections (edges)
    for i, conn in enumerate(sorted_connections):
        source_id = conn.get("source")
        target_id = conn.get("target")
        
        if not source_id or not target_id:
            continue
            
        # Get event type for color
        event_type = conn.get("event")
        edge_color = event_colors.get(event_type, "#7f7f7f")  # Gray default
        
        # Position nodes vertically on timeline (more space between them)
        y_pos = timeline_height - i
        
        # Position source node on the left, target on the right
        # Use wider spacing for better readability
        source_x = 1
        target_x = 5
        
        # Store positions for node rendering
        node_positions[source_id] = (source_x, y_pos)
        node_positions[target_id] = (target_x, y_pos)
        
        # Draw connection line with arrow
        ax.annotate("", 
                   xy=(target_x - 0.2, y_pos), 
                   xytext=(source_x + 0.2, y_pos),
                   arrowprops=dict(arrowstyle="->", color=edge_color, lw=2, alpha=0.9))
        
        # Add connection timestamp with more visibility
        ts = conn.get("timestamp", 0)
        if ts > 0:
            time_str = f"{ts:.2f}s"
            ax.text((source_x + target_x) / 2, y_pos + 0.1, time_str, 
                   ha='center', va='bottom', fontsize=9, alpha=0.8, 
                   bbox=dict(facecolor='white', alpha=0.7, pad=1, boxstyle='round'))
        
        # Add topic name with better visibility and shorter display
        topic = conn.get("topic", "")
        if topic:
            # Extract just the last part of the topic path for cleaner display
            topic_short = topic.split('/')[-1]
            ax.text((source_x + target_x) / 2, y_pos - 0.1, 
                   topic_short, ha='center', va='top', fontsize=8, alpha=0.7,
                   bbox=dict(facecolor='white', alpha=0.5, pad=1, boxstyle='round'))
            
        # Get event name for display
        event_names_dict = {
            0: "Info",
            1: "Start",
            2: "End",
            3: "Error",
            4: "Success"
        }
        if event_type in event_names_dict:
            event_name = event_names_dict[event_type]
            # Add event type label near the arrow
            ax.text((source_x + target_x) / 2, y_pos - 0.25, 
                   event_name, ha='center', va='top', fontsize=7, 
                   color=edge_color, weight='bold')
    
    # Now draw nodes with labels (to be on top of edges)
    for node_id, (x, y) in node_positions.items():
        # Get node data from our lookup dictionary
        node_data = node_data_by_id.get(node_id)
        
        if not node_data:
            continue
        
        # Get node properties
        node_type = node_data.get("type", "unknown")
        node_name = node_data.get("name", node_id)
        
        # Clean up node name if it's too long
        if len(node_name) > 20:
            node_name = f"{node_name[:17]}..."
            
        # Get color based on node type
        node_color = node_type_colors.get(node_type, "#7f7f7f")
        
        # Draw node with larger marker for better visibility
        ax.scatter(x, y, color=node_color, s=150, zorder=3, edgecolor='white')
        
        # Add node name with background for better readability
        # Position text away from the node with more space
        text_x = x - 0.2 if x == 1 else x + 0.2
        alignment = 'right' if x == 1 else 'left'
        
        ax.text(text_x, y, node_name, fontsize=10, 
                ha=alignment, va='center', zorder=4,
                bbox=dict(facecolor='white', alpha=0.8, pad=2, boxstyle='round'))
    
    # Highlight current time if provided
    if current_time is not None:
        # Find the closest connection to the current time
        closest_idx = 0
        min_diff = float('inf')
        
        for i, conn in enumerate(sorted_connections):
            ts = conn.get("timestamp", 0)
            diff = abs(ts - current_time)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        
        # Highlight the line corresponding to current time with more visibility
        if closest_idx < len(sorted_connections):
            y_pos = timeline_height - closest_idx
            ax.axhline(y_pos, color='red', linestyle='--', linewidth=2, alpha=0.7)
            ax.text(0.6, y_pos + 0.15, "Current Time", color='red', fontweight='bold', fontsize=10)
    
    # Format the plot
    ax.set_title("Robot Thinking Pattern Visualization", fontsize=16, pad=20)
    
    # Set column headers
    ax.text(1, timeline_height + 1, "SOURCE NODES", ha='center', va='bottom', 
           fontsize=12, fontweight='bold', color=node_type_colors["source"])
    ax.text(5, timeline_height + 1, "TARGET NODES", ha='center', va='bottom', 
           fontsize=12, fontweight='bold', color=node_type_colors["target"])
    
    # Hide axis ticks for cleaner look
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Add grid lines for better readability
    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
    
    # Set limits with padding
    ax.set_xlim(0, 6)
    if timeline_height > 0:
        ax.set_ylim(0.5, timeline_height + 1.5)
    
    # Create legend for node types
    node_legend_elements = []
    for node_type, color in node_type_colors.items():
        node_legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                     markerfacecolor=color, markersize=10, 
                                     label=f"{node_type.capitalize()} Node"))
    
    # Create legend for event types
    event_legend_elements = []
    event_names_dict = {
        0: "Info",
        1: "Start",
        2: "End",
        3: "Error",
        4: "Success"
    }
    for event_type, color in event_colors.items():
        if event_type in event_names_dict:
            event_legend_elements.append(plt.Line2D([0], [0], color=color, lw=2,
                                         label=f"{event_names_dict[event_type]} Event"))
    
    # Add the legends with better positioning
    legend1 = ax.legend(handles=node_legend_elements, loc='upper left', 
                        title="Node Types", fontsize='medium', title_fontsize='medium',
                        bbox_to_anchor=(0.01, 0.99))
    ax.add_artist(legend1)
    
    legend2 = ax.legend(handles=event_legend_elements, loc='upper right', 
                      title="Event Types", fontsize='medium', title_fontsize='medium',
                      bbox_to_anchor=(0.99, 0.99))
    
    plt.tight_layout()
    return fig

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
