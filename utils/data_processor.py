import json
import pandas as pd
from datetime import datetime
import io

def validate_json_data(content):
    """
    Validate if the content is a properly formatted JSON file with robot data.
    
    Args:
        content: The binary content of the uploaded file
        
    Returns:
        bool: True if the file is valid, False otherwise
    """
    try:
        # Try to parse the JSON
        data = json.loads(content)
        
        # Basic validation - check for essential robot data elements
        # This validation should be customized based on the expected format
        required_elements = ["metadata", "topics", "messages"]
        
        # For more flexible validation, check if at least one required element exists
        if not any(elem in data for elem in required_elements):
            # Alternative validation: check if there's any robot state data
            robot_data_indicators = ["pose", "position", "orientation", "twist", "joint_states"]
            if not any(indicator in str(data) for indicator in robot_data_indicators):
                return False
                
        return True
    except Exception:
        return False

def process_robot_data(content):
    """
    Process robot data from JSON content.
    
    Args:
        content: The binary content of the uploaded file
        
    Returns:
        dict: Processed data ready for visualization
    """
    # Parse JSON data
    if isinstance(content, bytes):
        data = json.loads(content)
    else:
        data = content
    
    result = {}
    
    # Process time range if available
    result["time_range"] = extract_time_range(data)
    
    # Extract time series data
    result["time_series"] = extract_time_series(data)
    
    # Extract robot state information
    result["robot_state"] = extract_robot_state(data)
    
    # Extract topic metadata
    result["topic_metadata"] = extract_topic_metadata(data)
    
    return result

def extract_time_range(data):
    """
    Extract the time range of the data.
    
    Args:
        data: The parsed JSON data
        
    Returns:
        tuple: (min_time, max_time)
    """
    min_time = 0
    max_time = 100  # Default if no time data available
    
    # Look for timestamps in the data
    if "messages" in data:
        timestamps = []
        for msg in data["messages"]:
            if "timestamp" in msg:
                timestamps.append(msg["timestamp"])
        
        if timestamps:
            min_time = min(timestamps)
            max_time = max(timestamps)
    
    # Look for alternative time representations
    elif "time_series" in data:
        times = []
        for series in data["time_series"]:
            if "times" in series:
                times.extend(series["times"])
        
        if times:
            min_time = min(times)
            max_time = max(times)
    
    return (min_time, max_time)

def extract_time_series(data):
    """
    Extract time series data from the JSON.
    
    Args:
        data: The parsed JSON data
        
    Returns:
        dict: Time series data organized by topic
    """
    time_series = {}
    
    # Handle standard ROS-like message format
    if "messages" in data:
        # Group messages by topic
        topic_messages = {}
        for msg in data["messages"]:
            if "topic" in msg and "data" in msg:
                topic = msg["topic"]
                if topic not in topic_messages:
                    topic_messages[topic] = []
                
                # Add timestamp if available
                entry = {"data": msg["data"]}
                if "timestamp" in msg:
                    entry["time"] = msg["timestamp"]
                
                topic_messages[topic].append(entry)
        
        # Convert grouped messages to time series
        for topic, messages in topic_messages.items():
            if messages:
                # Try to convert to a format suitable for plotting
                converted_data = []
                for msg in messages:
                    if isinstance(msg["data"], dict):
                        # Flatten one level of nested data
                        entry = {"time": msg.get("time", 0)}
                        for key, value in msg["data"].items():
                            if isinstance(value, (int, float)):
                                entry[key] = value
                        converted_data.append(entry)
                    elif isinstance(msg["data"], (int, float)):
                        converted_data.append({
                            "time": msg.get("time", 0),
                            "value": msg["data"]
                        })
                
                if converted_data:
                    time_series[topic] = converted_data
    
    # Handle direct time series format
    elif "time_series" in data:
        for series in data["time_series"]:
            if "name" in series and "values" in series:
                topic = series["name"]
                values = series["values"]
                
                # Associate with timestamps if available
                if "times" in series and len(series["times"]) == len(values):
                    time_series[topic] = [
                        {"time": t, "value": v} 
                        for t, v in zip(series["times"], values)
                    ]
                else:
                    # Create sequential time points if no timestamps
                    time_series[topic] = [
                        {"time": i, "value": v} 
                        for i, v in enumerate(values)
                    ]
    
    return time_series

def extract_robot_state(data):
    """
    Extract robot state information.
    
    Args:
        data: The parsed JSON data
        
    Returns:
        dict: Robot state data organized by timestamp
    """
    state_data = {}
    
    # Extract state data from various possible formats
    if "messages" in data:
        for msg in data["messages"]:
            if "timestamp" in msg and "data" in msg:
                timestamp = msg["timestamp"]
                
                # Check if this message contains robot state information
                if isinstance(msg["data"], dict):
                    state_info = {}
                    
                    # Look for position data
                    if "position" in msg["data"] or "pose" in msg["data"]:
                        position_data = msg["data"].get("position", msg["data"].get("pose", {}).get("position", {}))
                        if position_data:
                            state_info["position"] = position_data
                    
                    # Look for orientation data
                    if "orientation" in msg["data"] or "pose" in msg["data"]:
                        orientation_data = msg["data"].get("orientation", msg["data"].get("pose", {}).get("orientation", {}))
                        if orientation_data:
                            state_info["orientation"] = orientation_data
                    
                    # Look for joint states
                    if "joint_states" in msg["data"]:
                        joint_data = msg["data"]["joint_states"]
                        if joint_data:
                            state_info["joints"] = joint_data
                    
                    # Store the state data if we found relevant information
                    if state_info:
                        state_data[timestamp] = state_info
    
    # If no state data found, try alternative formats
    if not state_data and "poses" in data:
        for timestamp, pose in data["poses"].items():
            state_data[timestamp] = {"position": pose.get("position", {}), "orientation": pose.get("orientation", {})}
    
    return state_data

def extract_topic_metadata(data):
    """
    Extract metadata about the topics in the data.
    
    Args:
        data: The parsed JSON data
        
    Returns:
        dict: Topic metadata
    """
    topic_metadata = {}
    
    # Extract from standard ROS-like format
    if "topics" in data:
        for topic_info in data["topics"]:
            if "name" in topic_info:
                topic_name = topic_info["name"]
                topic_metadata[topic_name] = {
                    "type": topic_info.get("type", "unknown"),
                    "description": topic_info.get("description", "")
                }
    
    # If no explicit topic definitions, infer from messages
    elif "messages" in data:
        for msg in data["messages"]:
            if "topic" in msg and msg["topic"] not in topic_metadata:
                topic_metadata[msg["topic"]] = {
                    "type": "inferred",
                    "description": ""
                }
    
    return topic_metadata
