import streamlit as st
import pandas as pd
import json
import os
import time
import tempfile
import numpy as np
from utils.data_processor import process_robot_data, validate_json_data
from utils.visualization_utils import create_event_timeline, get_available_topics, create_node_path_visualization

# Set page configuration
st.set_page_config(
    page_title="Robot Data Visualizer",
    page_icon="🤖",
    layout="wide",
)

# Add minimal CSS for functional styling
st.markdown("""
<style>
.stSelectbox div[role="combobox"] > div {
    min-width: 100%;
}
</style>
""", unsafe_allow_html=True)

# Main title
st.title("Robot Path Visualizer")
st.markdown("Upload JSON robot data files to visualize node paths and robot operations")

# Sidebar for controls
st.sidebar.header("Controls")

# File upload section
uploaded_file = st.sidebar.file_uploader("Upload JSON Robot Data", type=["json"])

# Initialize session state variables if they don't exist
if "data" not in st.session_state:
    st.session_state.data = None
if "topics" not in st.session_state:
    st.session_state.topics = []
if "selected_topics" not in st.session_state:
    st.session_state.selected_topics = []
if "playback_speed" not in st.session_state:
    st.session_state.playback_speed = 1.0
if "current_time" not in st.session_state:
    st.session_state.current_time = 0
if "is_playing" not in st.session_state:
    st.session_state.is_playing = False
if "temp_file_path" not in st.session_state:
    st.session_state.temp_file_path = None

# Process uploaded file
if uploaded_file is not None:
    try:
        # Read and validate the uploaded JSON file
        content = uploaded_file.read()
        if validate_json_data(content):
            # Save to temporary file for Foxglove to access
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_file:
                tmp_file.write(content)
                st.session_state.temp_file_path = tmp_file.name

            # Process the data for visualization
            st.session_state.data = process_robot_data(content)
            
            # Extract available topics
            st.session_state.topics = get_available_topics(st.session_state.data)
            
            # Initialize selected topics if empty
            if not st.session_state.selected_topics and st.session_state.topics:
                st.session_state.selected_topics = st.session_state.topics[:min(3, len(st.session_state.topics))]
            
            st.sidebar.success("File successfully loaded!")
        else:
            st.sidebar.error("Invalid robot data format. Please upload a valid JSON file.")
    except Exception as e:
        st.sidebar.error(f"Error processing file: {str(e)}")

# Display topics and filters if data is loaded
if st.session_state.data is not None:
    # Topic selection
    st.sidebar.subheader("Data Streams")
    st.session_state.selected_topics = st.sidebar.multiselect(
        "Select topics to visualize",
        options=st.session_state.topics,
        default=st.session_state.selected_topics
    )
    
    # Main content area
if st.session_state.data is None:
    # Display instructions when no data is loaded
    st.title("Robot Path Visualization Tool")
    
    st.markdown("""
    This tool allows you to visualize and analyze robot data from JSON files, with a focus on ROS (Robot Operating System) messages.
    
    ## Getting Started
    1. Upload your JSON robot data file using the sidebar
    2. The app will automatically process and extract relevant data
    3. Use the visualization tabs to explore different aspects of the data
    
    ## Visualization Features
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Node Path Visualization")
        st.markdown("""
        - Visualize the robot's "thinking pattern" with clear node names
        - See direct connections between source and target nodes
        - Track the flow of information with color-coded event types
        - Understand complex decision-making processes
        """)
        
        st.subheader("JSON Data Viewer")
        st.markdown("""
        - Inspect the raw data structure from the uploaded file
        - Browse through the JSON object hierarchy
        - Filter data based on selected topics
        - Look for patterns in the robot data
        """)
    
    with col2:
        st.subheader("Interactive Features")
        st.markdown("""
        - Click and drag to move around the visualization
        - Zoom in/out to focus on specific areas
        - Select nodes to highlight connections
        - Find shortest paths between capabilities
        """)
        
        st.subheader("Playback Controls")
        st.markdown("""
        - Animation controls to visualize changes over time
        - Timeline slider for precise time selection
        - Play/pause and reset functionality
        """)
    
    st.markdown("""
    ## Supported Data Formats
    
    The application primarily supports JSON files with ROS bridge messages, including:
    
    - Standard ROS message format with topic, timestamp, and data
    - ROS bridge messages with operation, topic, and message content
    - Robot state information including position, orientation, and joint states
    - Capability events and state transitions
    
    **Start by uploading a JSON file using the file uploader in the sidebar!**
    """)
    
else:
    # Create tabs for different visualization aspects
    tab1, tab2 = st.tabs(["Node Path Visualization", "JSON Data Viewer"])
    
    with tab1:
        st.subheader("Robot Thinking Pattern")
        
        # Create node path visualization
        node_path_height = 600
        
        # Create node path visualization
        node_path_fig = create_node_path_visualization(
            data=st.session_state.data,
            current_time=st.session_state.current_time,
            height=node_path_height
        )
        
        if node_path_fig:
            st.pyplot(node_path_fig)
            
            # Add explanation of the visualization
            st.markdown("""
            ### Understanding the Node Path Visualization
            
            This visualization shows the robot's "thinking pattern" by displaying the flow between source nodes (left) and target nodes (right).
            
            - **Source Nodes**: Represent the origin points of events or commands (shown in green)
            - **Target Nodes**: Represent the destination or affected components (shown in blue)
            - **Connection Lines**: Show the flow of information between nodes, with color indicating the event type
            
            The visualization is arranged chronologically from top to bottom, with timestamps shown on each connection.
            """)
        else:
            st.info("No node path data available for visualization. Try uploading a file with robot event data.")
    
    with tab2:
        st.subheader("Input JSON Data")
        
        # Create visualization using native Streamlit/matplotlib
        timeline_height = 600
        
        # Create event timeline
        timeline_fig = create_event_timeline(
            data=st.session_state.data,
            selected_topics=st.session_state.selected_topics,
            current_time=st.session_state.current_time,
            height=timeline_height
        )
        
        if timeline_fig:
            st.pyplot(timeline_fig)
            
            # Add explanation of the JSON data viewer
            st.markdown("""
            ### Understanding the JSON Data
            
            This viewer shows the raw JSON data from the uploaded file.
            
            - **Browse**: Expand/collapse sections to explore the data structure
            - **Search**: Use your browser's search function to find specific values
            - **Filter**: Data is filtered based on your selected topics in the sidebar
            
            The JSON view helps inspect the exact data structure and values.
            """)
        else:
            st.info("No JSON data available for viewing. Try uploading a file with robot data.")



# Clean up temporary file when the app is closed
if hasattr(st, 'on_session_end'):
    @st.on_session_end
    def cleanup():
        if st.session_state.temp_file_path and os.path.exists(st.session_state.temp_file_path):
            try:
                os.unlink(st.session_state.temp_file_path)
            except:
                pass
