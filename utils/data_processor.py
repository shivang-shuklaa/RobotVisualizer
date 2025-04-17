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
        
        # Check if it's an array of ROS bridge messages
        if isinstance(data, list) and len(data) > 0:
            # Check for ROS bridge format (messages with op, topic, and msg fields)
            if all(isinstance(item, dict) for item in data):
                ros_bridge_format = any("op" in item and "topic" in item and "msg" in item for item in data[:10])
                if ros_bridge_format:
                    return True
        
        # Check for other standard ROS formats
        required_elements = ["metadata", "topics", "messages"]
        
        # For more flexible validation, check if at least one required element exists
        if isinstance(data, dict) and any(elem in data for elem in required_elements):
            return True
                
        # Alternative validation: check if there's any robot state data
        robot_data_indicators = ["pose", "position", "orientation", "twist", "joint_states"]
        if any(indicator in str(data) for indicator in robot_data_indicators):
            return True
                
        return False
    except Exception as e:
        print(f"Validation error: {str(e)}")
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
    
    # Check if it's ROSBridge format (list of messages)
    if isinstance(data, list) and len(data) > 0 and all(isinstance(item, dict) for item in data):
        # Try to extract timestamps from message headers
        timestamps = []
        
        for msg_data in data:
            if "msg" in msg_data and isinstance(msg_data["msg"], dict):
                # Look for header with timestamp
                if "header" in msg_data["msg"] and "stamp" in msg_data["msg"]["header"]:
                    stamp = msg_data["msg"]["header"]["stamp"]
                    if "secs" in stamp and "nsecs" in stamp:
                        # Convert to seconds (float) for easier processing
                        ts = float(stamp["secs"]) + float(stamp["nsecs"]) / 1e9
                        timestamps.append(ts)
        
        if timestamps:
            min_time = min(timestamps)
            max_time = max(timestamps)
            return (min_time, max_time)
    
    # Look for timestamps in the standard format
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
    
    # Check if it's ROSBridge format (list of messages)
    if isinstance(data, list) and len(data) > 0 and all(isinstance(item, dict) for item in data):
        # Group messages by topic
        topic_messages = {}
        
        # First pass: collect all messages and timestamps
        for msg_data in data:
            if "op" in msg_data and msg_data["op"] == "publish" and "topic" in msg_data and "msg" in msg_data:
                topic = msg_data["topic"]
                msg_content = msg_data["msg"]
                
                if topic not in topic_messages:
                    topic_messages[topic] = []
                
                # Extract timestamp from header if available
                timestamp = 0
                if isinstance(msg_content, dict) and "header" in msg_content and "stamp" in msg_content["header"]:
                    stamp = msg_content["header"]["stamp"]
                    if "secs" in stamp and "nsecs" in stamp:
                        timestamp = float(stamp["secs"]) + float(stamp["nsecs"]) / 1e9
                
                # Use sequential index if timestamp is 0
                if timestamp == 0:
                    timestamp = len(topic_messages[topic])
                
                # Process message content
                entry = {"time": timestamp, "msg": msg_content}
                topic_messages[topic].append(entry)
        
        # Convert grouped messages to time series format
        for topic, messages in topic_messages.items():
            if messages:
                # Sort messages by timestamp
                messages.sort(key=lambda x: x["time"])
                
                # Check if this is the capabilities topic
                if topic == "/capabilities/events":
                    # Special handling for capabilities events
                    converted_data = []
                    message_index = 0
                    for msg in messages:
                        # Use increasing index for x-axis
                        entry = {"index": message_index}
                        message_index += 1
                        
                        # Add timestamp 
                        entry["time"] = msg["time"]
                        
                        # Extract event information from targets
                        if "target" in msg["msg"] and isinstance(msg["msg"]["target"], dict):
                            target = msg["msg"]["target"]
                            
                            # Track event type as value (using integer for better plotting)
                            if "event" in target:
                                entry["event"] = float(target["event"])
                            
                            # Add thread_id as a numeric value
                            if "thread_id" in target:
                                entry["thread_id"] = float(target["thread_id"])
                                
                            # Check if server is ready
                            if "server_ready" in target:
                                entry["server_ready"] = 1.0 if target["server_ready"] else 0.0
                                
                            # Check if there was an error
                            if "error" in target:
                                entry["error"] = 1.0 if target["error"] else 0.0
                        
                        # Only add entry if it has some numeric values
                        if len(entry) > 2:  # more than just index and time
                            converted_data.append(entry)
                    
                    if converted_data:
                        time_series[topic] = converted_data
                else:
                    # Generic handling for other topics
                    converted_data = []
                    message_index = 0
                    for msg in messages:
                        entry = {"index": message_index, "time": msg["time"]}
                        message_index += 1
                        
                        # Extract values from message content
                        found_values = False
                        if isinstance(msg["msg"], dict):
                            # Extract first level numeric values
                            for key, value in msg["msg"].items():
                                if isinstance(value, (int, float)):
                                    entry[key] = float(value)
                                    found_values = True
                            
                            # Try to extract values from 'target' if present
                            if "target" in msg["msg"] and isinstance(msg["msg"]["target"], dict):
                                for key, value in msg["msg"]["target"].items():
                                    if isinstance(value, (int, float)) and key not in entry:
                                        entry[f"target_{key}"] = float(value)
                                        found_values = True
                            
                            # Try to extract values from 'source' if present
                            if "source" in msg["msg"] and isinstance(msg["msg"]["source"], dict):
                                for key, value in msg["msg"]["source"].items():
                                    if isinstance(value, (int, float)) and key not in entry:
                                        entry[f"source_{key}"] = float(value)
                                        found_values = True
                        
                        # Always include the entry with at least the index and time
                        if not found_values:
                            # Add a default value for plotting
                            entry["value"] = 1.0
                        
                        converted_data.append(entry)
                    
                    if converted_data:
                        time_series[topic] = converted_data
        
        return time_series
    
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
    
    # Check if it's ROSBridge format (list of messages)
    if isinstance(data, list) and len(data) > 0 and all(isinstance(item, dict) for item in data):
        for msg_data in data:
            if "op" in msg_data and msg_data["op"] == "publish" and "topic" in msg_data and "msg" in msg_data:
                msg_content = msg_data["msg"]
                
                # Skip if not a dictionary or doesn't have a header
                if not isinstance(msg_content, dict):
                    continue
                
                # Extract timestamp from header if available
                timestamp = 0
                if "header" in msg_content and "stamp" in msg_content["header"]:
                    stamp = msg_content["header"]["stamp"]
                    if "secs" in stamp and "nsecs" in stamp:
                        timestamp = float(stamp["secs"]) + float(stamp["nsecs"]) / 1e9
                
                # Skip processing if no timestamp found
                if timestamp == 0:
                    continue
                
                state_info = {}
                
                # Check for position/pose data
                if "pose" in msg_content:
                    pose_data = msg_content["pose"]
                    if isinstance(pose_data, dict):
                        if "position" in pose_data:
                            state_info["position"] = pose_data["position"]
                        if "orientation" in pose_data:
                            state_info["orientation"] = pose_data["orientation"]
                
                # Check for target/source information that might contain position
                if "target" in msg_content and isinstance(msg_content["target"], dict):
                    target_data = msg_content["target"]
                    # Extract important text information
                    if "text" in target_data:
                        state_info["status"] = target_data["text"]
                    # Extract event information
                    if "event" in target_data:
                        state_info["event"] = target_data["event"]
                
                # Check for source information
                if "source" in msg_content and isinstance(msg_content["source"], dict):
                    source_data = msg_content["source"]
                    # Get capability info
                    if "capability" in source_data:
                        state_info["capability"] = source_data["capability"]
                
                # Store state data if we found relevant information
                if state_info:
                    # Convert timestamp to string for dictionary key
                    state_data[str(timestamp)] = state_info
        
        # If we found state data, return it
        if state_data:
            return state_data
    
    # Extract state data from other formats if ROSBridge format didn't work
    if isinstance(data, dict):
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
                            state_data[str(timestamp)] = state_info
        
        # If no state data found, try alternative formats
        if not state_data and "poses" in data:
            for timestamp, pose in data["poses"].items():
                state_data[str(timestamp)] = {"position": pose.get("position", {}), "orientation": pose.get("orientation", {})}
    
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
    
    # Check if it's ROSBridge format (list of messages)
    if isinstance(data, list) and len(data) > 0 and all(isinstance(item, dict) for item in data):
        # Collect topics from all messages
        for msg_data in data:
            if "topic" in msg_data and "op" in msg_data:
                topic = msg_data["topic"]
                if topic not in topic_metadata:
                    # Determine message type from the message content
                    msg_type = "unknown"
                    if "msg" in msg_data and isinstance(msg_data["msg"], dict):
                        # Try to infer type from content
                        if "header" in msg_data["msg"]:
                            msg_type = "std_msgs/Header"
                        if "pose" in msg_data["msg"]:
                            msg_type = "geometry_msgs/Pose"
                        elif "source" in msg_data["msg"] and "target" in msg_data["msg"]:
                            msg_type = "capabilities_msgs/Event"
                    
                    topic_metadata[topic] = {
                        "type": msg_type,
                        "description": "Inferred from ROS Bridge messages"
                    }
        
        # If we found topic metadata, return it
        if topic_metadata:
            return topic_metadata
    
    # Handle standard ROS-like format for dictionary data
    if isinstance(data, dict):
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
