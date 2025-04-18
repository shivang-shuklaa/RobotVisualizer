import streamlit as st
import pandas as pd
import json
import os
import time
import tempfile
import numpy as np
from utils.data_processor import process_robot_data, validate_json_data
from utils.foxglove_integration import create_event_timeline, get_available_topics, create_node_path_visualization

# Set page configuration
st.set_page_config(
    page_title="Robot Data Visualizer",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply dark mode styling via Streamlit theme override
st.markdown("""
    <style>
        body, .stApp, .block-container {
            background-color: #1e1e1e;
            color: #f0f0f0;
        }
        .st-c8, .st-dv, .st-dw, .st-dx, .st-cf, .st-eh {
            background-color: #2c2c2c !important;
        }
        .stButton>button {
            background-color: #4CAF50;
            color: white;
        }
        .stTextInput>div>div>input {
            background-color: #2c2c2c;
            color: white;
        }
        .stSelectbox>div>div>div>input {
            background-color: #2c2c2c;
            color: white;
        }
        .stSlider>div>div {
            color: white;
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
        content = uploaded_file.read()
        if validate_json_data(content):
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_file:
                tmp_file.write(content)
                st.session_state.temp_file_path = tmp_file.name

            st.session_state.data = process_robot_data(content)
            st.session_state.topics = get_available_topics(st.session_state.data)
            if not st.session_state.selected_topics and st.session_state.topics:
                st.session_state.selected_topics = st.session_state.topics[:min(3, len(st.session_state.topics))]

            st.sidebar.success("File successfully loaded!")
        else:
            st.sidebar.error("Invalid robot data format. Please upload a valid JSON file.")
    except Exception as e:
        st.sidebar.error(f"Error processing file: {str(e)}")

# Sidebar UI for filters and playback
if st.session_state.data is not None:
    st.sidebar.subheader("Data Streams")
    st.session_state.selected_topics = st.sidebar.multiselect(
        "Select topics to visualize",
        options=st.session_state.topics,
        default=st.session_state.selected_topics
    )

    st.sidebar.subheader("Playback Controls")
    st.session_state.playback_speed = st.sidebar.slider("Playback Speed", 0.1, 2.0, st.session_state.playback_speed, 0.1)
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Play" if not st.session_state.is_playing else "Pause"):
            st.session_state.is_playing = not st.session_state.is_playing
    with col2:
        if st.button("Reset"):
            st.session_state.current_time = 0
            st.session_state.is_playing = False

    if "time_range" in st.session_state.data:
        min_time, max_time = st.session_state.data["time_range"]
        st.session_state.current_time = st.sidebar.slider(
            "Timeline",
            float(min_time), float(max_time), float(st.session_state.current_time), step=0.1
        )

# Main interface
if st.session_state.data is None:
    st.title("Robot Path Visualization Tool")
    st.markdown("""
    This tool allows you to visualize and analyze robot data from JSON files.
    - Upload a file from the sidebar.
    - Visualize node paths and system behaviors.
    """)
else:
    tab1, tab2 = st.tabs(["Node Path Visualization", "JSON Data Viewer"])

    with tab1:
        st.subheader("Robot Thinking Pattern")
        node_path_height = 600
        node_path_fig = create_node_path_visualization(
            data=st.session_state.data,
            current_time=st.session_state.current_time,
            height=node_path_height
        )
        if node_path_fig:
            st.pyplot(node_path_fig)

            # Explanation - always visible
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
        json_height = 600
        timeline_fig = create_event_timeline(
            data=st.session_state.data,
            selected_topics=st.session_state.selected_topics,
            current_time=st.session_state.current_time,
            height=json_height
        )
        
        if timeline_fig:
            st.pyplot(timeline_fig)
            
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

# Playback animation
if st.session_state.is_playing:
    time.sleep(0.1)
    st.session_state.current_time += st.session_state.playback_speed
    st.rerun()

# Cleanup temporary file
if hasattr(st, 'on_session_end'):
    @st.on_session_end
    def cleanup():
        if st.session_state.temp_file_path and os.path.exists(st.session_state.temp_file_path):
            try:
                os.unlink(st.session_state.temp_file_path)
            except:
                pass