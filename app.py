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
)

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
    
    # Playback controls
    st.sidebar.subheader("Playback Controls")
    
    # Playback speed
    st.session_state.playback_speed = st.sidebar.slider(
        "Playback Speed",
        min_value=0.1,
        max_value=2.0,
        value=st.session_state.playback_speed,
        step=0.1
    )
    
    # Play/Pause button
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Play" if not st.session_state.is_playing else "Pause"):
            st.session_state.is_playing = not st.session_state.is_playing
    
    # Reset button
    with col2:
        if st.button("Reset"):
            st.session_state.current_time = 0
            st.session_state.is_playing = False
    
    # Time slider
    if "time_range" in st.session_state.data:
        min_time, max_time = st.session_state.data["time_range"]
        # Convert all values to float to avoid type mismatch
        min_time_float = float(min_time)
        max_time_float = float(max_time)
        current_time_float = float(st.session_state.current_time)
        
        st.session_state.current_time = st.sidebar.slider(
            "Timeline",
            min_value=min_time_float,
            max_value=max_time_float,
            value=current_time_float,
            step=float(0.1)  # Explicitly convert to float
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
        
        st.subheader("Event Timeline")
        st.markdown("""
        - Chronological view of robot events over time
        - Track capability activations and state changes
        - Identify patterns in robot behavior
        """)
        
        st.subheader("Time Series Data")
        st.markdown("""
        - Plot sensor readings and state changes over time
        - Filter specific topics for detailed analysis
        - Compare multiple data streams
        """)
    
    with col2:
        st.subheader("Robot State")
        st.markdown("""
        - View current robot state at any point in time
        - Position and orientation information
        - Joint states and system status
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
    tab1, tab2, tab3, tab4 = st.tabs(["Node Path Visualization", "Timeline Events", "Time Series Data", "Robot State"])
    
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
        st.subheader("Event Timeline")
        
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
            
            # Add explanation of the visualization
            st.markdown("""
            ### Understanding the Event Timeline
            
            This visualization shows robot events over time as a chronological timeline.
            
            - **Event Types**: Different colors represent different event types (Info, Start, End, Error, Success)
            - **Capabilities**: Horizontal bars show which capability was involved in each event
            - **Messages**: Text messages provide additional context for events
            
            The timeline helps identify patterns and sequences in robot operations.
            """)
        else:
            st.info("No timeline data available for visualization. Try uploading a file with robot event data.")
    
    with tab3:
        st.subheader("Sensor Data Time Series")
        
        # Display time series data if available
        if "time_series" in st.session_state.data:
            time_series_data = st.session_state.data["time_series"]
            
            # Filter for selected topics
            filtered_data = {topic: data for topic, data in time_series_data.items() 
                            if topic in st.session_state.selected_topics}
            
            if filtered_data:
                # Convert to DataFrame for easier plotting
                for topic, values in filtered_data.items():
                    df = pd.DataFrame(values)
                    if not df.empty:
                        st.subheader(f"{topic}")
                        
                        # Make sure all values are finite before plotting
                        for col in df.columns:
                            # Replace non-finite values with NaN so pandas can handle them
                            if df[col].dtype in ['float', 'int']:
                                # Use numpy's isinf instead of pandas
                                import numpy as np
                                df[col] = df[col].apply(lambda x: float('nan') if not pd.api.types.is_number(x) or pd.isna(x) or (isinstance(x, float) and np.isinf(x)) else x)
                        
                        # Choose an appropriate index for plotting
                        if 'index' in df.columns:
                            # Filter out any NaN values and reset index to avoid gaps
                            plotting_df = df.dropna(subset=['index']).copy()
                            if not plotting_df.empty:
                                # Use sequential numbers if there are any issues with the index
                                plotting_df['plot_index'] = range(len(plotting_df))
                                plotting_df = plotting_df.set_index('plot_index')
                                
                                # Select only finite numeric columns
                                numeric_cols = plotting_df.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns
                                # Exclude the original index column
                                if 'index' in numeric_cols:
                                    numeric_cols = [col for col in numeric_cols if col != 'index']
                                
                                if len(numeric_cols) > 0:
                                    st.line_chart(plotting_df[numeric_cols])
                                    
                                    # Provide additional info about the data
                                    with st.expander("Data Statistics"):
                                        st.write(plotting_df[numeric_cols].describe())
                                else:
                                    st.info(f"No valid numeric data to plot for {topic}")
                            else:
                                st.info(f"No valid data points for {topic}")
                        elif 'time' in df.columns:
                            # Filter out any NaN values and reset index to avoid gaps
                            plotting_df = df.dropna(subset=['time']).copy()
                            if not plotting_df.empty:
                                # Sort by time and use sequential indices for plotting
                                plotting_df = plotting_df.sort_values('time')
                                plotting_df['plot_index'] = range(len(plotting_df))
                                plotting_df = plotting_df.set_index('plot_index')
                                
                                # Select only finite numeric columns
                                numeric_cols = plotting_df.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns
                                
                                if len(numeric_cols) > 0:
                                    st.line_chart(plotting_df[numeric_cols])
                                    
                                    # Provide additional info about the data
                                    with st.expander("Data Statistics"):
                                        st.write(plotting_df[numeric_cols].describe())
                                else:
                                    st.info(f"No valid numeric data to plot for {topic}")
                            else:
                                st.info(f"No valid data points for {topic}")
                        else:
                            # Create a simple sequential index for plotting
                            df['plot_index'] = range(len(df))
                            plotting_df = df.set_index('plot_index')
                            
                            # Select only numeric columns
                            numeric_cols = plotting_df.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns
                            
                            if len(numeric_cols) > 0:
                                st.line_chart(plotting_df[numeric_cols])
                            else:
                                st.info(f"No numeric data to plot for {topic}")
            else:
                st.info("No time series data available for selected topics")
        else:
            st.info("No time series data available in the uploaded file")
    
    with tab4:
        st.subheader("Robot State")
        
        # Display current robot state information
        if "robot_state" in st.session_state.data and st.session_state.current_time is not None:
            state_data = st.session_state.data["robot_state"]
            
            # Find the closest time point to current_time
            if hasattr(state_data, "get"):
                current_state = state_data.get(str(st.session_state.current_time), state_data.get(list(state_data.keys())[0], {}))
                
                # Display state data in columns
                if current_state:
                    cols = st.columns(3)
                    col_index = 0
                    
                    # Position data
                    if "position" in current_state:
                        with cols[col_index % 3]:
                            st.subheader("Position")
                            pos = current_state["position"]
                            st.write(f"X: {pos.get('x', 0):.3f}")
                            st.write(f"Y: {pos.get('y', 0):.3f}")
                            st.write(f"Z: {pos.get('z', 0):.3f}")
                        col_index += 1
                    
                    # Orientation data
                    if "orientation" in current_state:
                        with cols[col_index % 3]:
                            st.subheader("Orientation")
                            orient = current_state["orientation"]
                            st.write(f"X: {orient.get('x', 0):.3f}")
                            st.write(f"Y: {orient.get('y', 0):.3f}")
                            st.write(f"Z: {orient.get('z', 0):.3f}")
                            st.write(f"W: {orient.get('w', 0):.3f}")
                        col_index += 1
                    
                    # Joint states data
                    if "joints" in current_state:
                        with cols[col_index % 3]:
                            st.subheader("Joint States")
                            for joint_name, joint_value in current_state["joints"].items():
                                st.write(f"{joint_name}: {joint_value:.3f}")
                        col_index += 1
                    
                    # Capability data
                    if "capability" in current_state:
                        with cols[col_index % 3]:
                            st.subheader("Capability")
                            st.write(current_state["capability"])
                        col_index += 1
                    
                    # Status information
                    if "status" in current_state:
                        with cols[col_index % 3]:
                            st.subheader("Status")
                            st.write(current_state["status"])
                        col_index += 1
                    
                    # Event information
                    if "event" in current_state:
                        with cols[col_index % 3]:
                            st.subheader("Event")
                            event_value = current_state["event"]
                            event_name = "Unknown"
                            # Map event codes to names
                            event_map = {
                                0: "Info",
                                1: "Start",
                                2: "End",
                                3: "Error",
                                4: "Success"
                            }
                            if event_value in event_map:
                                event_name = event_map[event_value]
                            st.write(f"{event_name} ({event_value})")
                else:
                    st.info("No state data available for the current time point")
            else:
                st.info("Robot state data is not in the expected format")
        else:
            st.info("No robot state data available in the uploaded file")

# Clean up temporary file when the app is closed
if hasattr(st, 'on_session_end'):
    @st.on_session_end
    def cleanup():
        if st.session_state.temp_file_path and os.path.exists(st.session_state.temp_file_path):
            try:
                os.unlink(st.session_state.temp_file_path)
            except:
                pass
