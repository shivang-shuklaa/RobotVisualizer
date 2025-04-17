import streamlit as st
import json
import os
import base64
import uuid

def create_foxglove_iframe(file_path, selected_topics=None, current_time=0, height=600):
    """
    Create an HTML iframe for Foxglove Studio visualization.
    
    Args:
        file_path: Path to the JSON file to visualize
        selected_topics: List of topics to display
        current_time: Current playback time
        height: Height of the iframe in pixels
        
    Returns:
        str: HTML content for the iframe
    """
    # Base Foxglove Studio URL
    foxglove_url = "https://studio.foxglove.dev/"
    
    # Create a unique data source ID
    data_source_id = str(uuid.uuid4())
    
    # Create a configuration for Foxglove
    config = {
        "layout": get_layout_config(selected_topics),
        "playbackConfig": {
            "speed": 1.0,
            "position": current_time
        },
        "dataSources": [
            {
                "id": data_source_id,
                "type": "file",
                "name": "Local JSON File",
                "fileType": "json",
                "filePath": file_path
            }
        ]
    }
    
    # Encode the configuration as a URI component
    config_json = json.dumps(config)
    encoded_config = base64.b64encode(config_json.encode('utf-8')).decode('utf-8')
    
    # Create the iframe HTML
    iframe_html = f"""
    <iframe
        src="{foxglove_url}?ds={encoded_config}"
        width="100%"
        height="{height}"
        frameborder="0"
        allow="autoplay; fullscreen"
        style="border: 1px solid #ddd; border-radius: 4px;"
    ></iframe>
    """
    
    return iframe_html

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
