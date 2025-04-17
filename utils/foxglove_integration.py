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
