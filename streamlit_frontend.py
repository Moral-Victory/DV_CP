import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# API endpoint
API_URL = "http://localhost:8000"

# Set page configuration
st.set_page_config(
    page_title="Machine Performance Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #111827;
        color: white;
    }
    .stApp {
        background-color: #111827;
    }
    h1, h2, h3, h4, h5, h6 {
        color: white !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1f2937;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #374151;
        border-radius: 5px;
    }
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .machine-card {
        background-color: #1f2937;
        border-radius: 10px;
        padding: 15px;
        transition: transform 0.2s;
        cursor: pointer;
    }
    .machine-card:hover {
        transform: translateY(-5px);
    }
    .operational {
        border-left: 5px solid #10b981;
    }
    .warning {
        border-left: 5px solid #f59e0b;
    }
    .failure {
        border-left: 5px solid #ef4444;
    }
    .stProgress > div > div > div > div {
        background-color: #111827;
    }
    .status-operational {
        color: #10b981;
    }
    .status-warning {
        color: #f59e0b;
    }
    .status-failure {
        color: #ef4444;
    }
</style>
""", unsafe_allow_html=True)

# Functions to fetch data from API
def get_all_lathes():
    try:
        response = requests.get(f"{API_URL}/lathes")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching lathes data: {e}")
        return []

def get_lathe_details(lathe_id):
    try:
        response = requests.get(f"{API_URL}/lathes/{lathe_id}")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching lathe details: {e}")
        return None

def get_lathe_sensor_data(lathe_id):
    try:
        response = requests.get(f"{API_URL}/lathes/{lathe_id}/sensor-data")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching lathe sensor data: {e}")
        return None

def get_lathe_product_analysis(lathe_id):
    try:
        response = requests.get(f"{API_URL}/lathes/{lathe_id}/product-analysis")
        return response.json()
    except Exception as e:
        st.error(f"Error fetching lathe product analysis: {e}")
        return None

# Custom components
def render_status_badge(status):
    if status == "Operational":
        return f"<span class='status-operational'>● {status}</span>"
    elif status == "Warning":
        return f"<span class='status-warning'>● {status}</span>"
    else:
        return f"<span class='status-failure'>● {status}</span>"

def render_health_bar(value):
    if value >= 80:
        color = "#10b981"  # green
    elif value >= 60:
        color = "#f59e0b"  # yellow
    else:
        color = "#ef4444"  # red
    
    return st.progress(value/100, text=f"{value}%")

def render_lathe_card(lathe):
    status_class = lathe["status"].lower()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
        <div class='machine-card {status_class}'>
            <h3>{lathe['name']} {render_status_badge(lathe['status'])}</h3>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Health Score")
        render_health_bar(lathe["health_score"])
    
    with col2:
        st.markdown("### Uptime")
        render_health_bar(lathe["uptime"])

def show_dashboard():
    st.title("Machine Performance Dashboard")
    st.markdown("Monitor performance, uptime, and health status of all lathe machines")
    
    # Fetch all lathes
    lathes = get_all_lathes()
    
    if not lathes:
        st.warning("No lathe data available. Please ensure the backend is running and MongoDB is populated.")
        return
    
    # Display lathe cards in a grid
    cols = st.columns(len(lathes) if len(lathes) <= 4 else 4)
    
    for i, lathe in enumerate(lathes):
        with cols[i % 4]:
            status_class = lathe["status"].lower()
            
            with st.container():
                st.markdown(f"""
                <div class='machine-card {status_class}'>
                    <h3>{lathe['name']} {render_status_badge(lathe['status'])}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("#### Health Score")
                render_health_bar(lathe["health_score"])
                
                st.markdown("#### Uptime")
                render_health_bar(lathe["uptime"])
                
                if st.button(f"View Details", key=f"btn_{lathe['lathe_id']}"):
                    st.session_state.selected_lathe = lathe["lathe_id"]
                    st.session_state.view = "lathe_details"
                    st.experimental_rerun()

def show_lathe_details():
    lathe_id = st.session_state.selected_lathe
    lathe_details = get_lathe_details(lathe_id)
    
    if not lathe_details:
        st.warning(f"No data available for Lathe M{lathe_id}")
        if st.button("← Back to Dashboard"):
            st.session_state.view = "dashboard"
            st.experimental_rerun()
        return
    
    # Back button
    col1, col2 = st.columns([1, 11])
    with col1:
        if st.button("← Back"):
            st.session_state.view = "dashboard"
            st.experimental_rerun()
    
    with col2:
        st.title(f"{lathe_details['name']} Details")
        st.markdown(f"Current Status: {render_status_badge(lathe_details['status'])}", unsafe_allow_html=True)
    
    # Tabs for different analysis
    tab1, tab2 = st.tabs(["Sensor Data Analysis", "Product Analysis"])
    
    # Sensor Data Tab
    with tab1:
        sensor_data = get_lathe_sensor_data(lathe_id)
        
        if not sensor_data:
            st.warning("Sensor data not available")
        else:
            # Key metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Health Score", f"{lathe_details['health_score']}%")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col2:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Uptime", f"{lathe_details['uptime']}%")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col3:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Failure Count", lathe_details['failure_count'])
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Sensor visualizations
            st.subheader("Sensor Readings")
            
            # Temperature charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Air Temperature
                fig = go.Figure()
                fig.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=sensor_data['stats']['air_temperature']['avg'],
                    title={"text": "Air Temperature [K]"},
                    gauge={
                        'axis': {'range': [sensor_data['stats']['air_temperature']['min'], 
                                          sensor_data['stats']['air_temperature']['max']]},
                        'bar': {'color': "#ef4444"},
                        'bgcolor': "gray",
                        'threshold': {
                            'line': {'color': "white", 'width': 2},
                            'thickness': 0.75,
                            'value': 310
                        }
                    }
                ))
                fig.update_layout(
                    height=250,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Process Temperature
                fig = go.Figure()
                fig.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=sensor_data['stats']['process_temperature']['avg'],
                    title={"text": "Process Temperature [K]"},
                    gauge={
                        'axis': {'range': [sensor_data['stats']['process_temperature']['min'], 
                                          sensor_data['stats']['process_temperature']['max']]},
                        'bar': {'color': "#ef4444"},
                        'bgcolor': "gray",
                        'threshold': {
                            'line': {'color': "white", 'width': 2},
                            'thickness': 0.75,
                            'value': 320
                        }
                    }
                ))
                fig.update_layout(
                    height=250,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            # Rotational Speed and Torque
            col1, col2 = st.columns(2)
            
            with col1:
                # Rotational Speed
                fig = go.Figure()
                fig.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=sensor_data['stats']['rotational_speed']['avg'],
                    title={"text": "Rotational Speed [rpm]"},
                    gauge={
                        'axis': {'range': [sensor_data['stats']['rotational_speed']['min'], 
                                          sensor_data['stats']['rotational_speed']['max']]},
                        'bar': {'color': "#10b981"},
                        'bgcolor': "gray",
                        'threshold': {
                            'line': {'color': "white", 'width': 2},
                            'thickness': 0.75,
                            'value': 1500
                        }
                    }
                ))
                fig.update_layout(
                    height=250,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                # Torque
                fig = go.Figure()
                fig.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=sensor_data['stats']['torque']['avg'],
                    title={"text": "Torque [Nm]"},
                    gauge={
                        'axis': {'range': [sensor_data['stats']['torque']['min'], 
                                          sensor_data['stats']['torque']['max']]},
                        'bar': {'color': "#10b981"},
                        'bgcolor': "gray",
                        'threshold': {
                            'line': {'color': "white", 'width': 2},
                            'thickness': 0.75,
                            'value': 50
                        }
                    }
                ))
                fig.update_layout(
                    height=250,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            # Tool Wear
            col1, col2 = st.columns(2)
            
            with col1:
                # Tool Wear
                fig = go.Figure()
                fig.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=sensor_data['stats']['tool_wear']['avg'],
                    title={"text": "Tool Wear [min]"},
                    gauge={
                        'axis': {'range': [sensor_data['stats']['tool_wear']['min'], 
                                          sensor_data['stats']['tool_wear']['max']]},
                        'bar': {'color': "#f59e0b"},
                        'bgcolor': "gray",
                        'threshold': {
                            'line': {'color': "white", 'width': 2},
                            'thickness': 0.75,
                            'value': 200
                        }
                    }
                ))
                fig.update_layout(
                    height=250,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                if "vibration" in sensor_data['stats']:
                    # Vibration
                    fig = go.Figure()
                    fig.add_trace(go.Indicator(
                        mode="gauge+number",
                        value=sensor_data['stats']['vibration']['avg'],
                        title={"text": "Vibration"},
                        gauge={
                            'axis': {'range': [sensor_data['stats']['vibration']['min'], 
                                              sensor_data['stats']['vibration']['max']]},
                            'bar': {'color': "#f59e0b"},
                            'bgcolor': "gray",
                            'threshold': {
                                'line': {'color': "white", 'width': 2},
                                'thickness': 0.75,
                                'value': 50
                            }
                        }
                    ))
                    fig.update_layout(
                        height=250,
                        paper_bgcolor="#1f2937",
                        plot_bgcolor="#1f2937",
                        font={'color': "white"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
            # Radar Chart comparing all parameters
            st.subheader("Parameter Comparison")
            
            # Normalize values for radar chart
            radar_data = {}
            for param in ['air_temperature', 'process_temperature', 'rotational_speed', 'torque', 'tool_wear']:
                min_val = sensor_data['stats'][param]['min']
                max_val = sensor_data['stats'][param]['max']
                avg_val = sensor_data['stats'][param]['avg']
                
                # Normalize to 0-1 range
                if max_val != min_val:
                    normalized = (avg_val - min_val) / (max_val - min_val)
                else:
                    normalized = 0.5
                
                radar_data[param] = normalized
            
            # Add vibration if available
            if "vibration" in sensor_data['stats']:
                min_val = sensor_data['stats']['vibration']['min']
                max_val = sensor_data['stats']['vibration']['max']
                avg_val = sensor_data['stats']['vibration']['avg']
                
                if max_val != min_val:
                    normalized = (avg_val - min_val) / (max_val - min_val)
                else:
                    normalized = 0.5
                
                radar_data['vibration'] = normalized
            
            # Create radar chart
            categories = list(radar_data.keys())
            values = list(radar_data.values())
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='Parameters',
                line_color='#10b981'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 1]
                    )
                ),
                height=400,
                paper_bgcolor="#1f2937",
                plot_bgcolor="#1f2937",
                font={'color': "white"}
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Product Analysis Tab
    with tab2:
        product_data = get_lathe_product_analysis(lathe_id)
        
        if not product_data:
            st.warning("Product analysis data not available")
        else:
            # Product Type Distribution
            st.subheader("Product Type Distribution")
            
            if product_data['product_types']:
                # Create pie chart
                fig = px.pie(
                    values=list(product_data['product_types'].values()),
                    names=list(product_data['product_types'].keys()),
                    title="Product Types"
                )
                fig.update_layout(
                    height=350,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Product Quality Analysis
                st.subheader("Product Quality Analysis")
                
                if product_data['product_quality']:
                    # Create bar chart for failure rates
                    product_types = list(product_data['product_quality'].keys())
                    failure_rates = [product_data['product_quality'][pt]['failure_rate'] for pt in product_types]
                    health_scores = [product_data['product_quality'][pt]['avg_health_score'] for pt in product_types]
                    
                    # Two column layout
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Failure Rate by Product Type
                        fig = px.bar(
                            x=product_types,
                            y=failure_rates,
                            labels={'x': 'Product Type', 'y': 'Failure Rate (%)'},
                            title="Failure Rate by Product Type",
                            color=failure_rates,
                            color_continuous_scale=['green', 'yellow', 'red']
                        )
                        fig.update_layout(
                            height=350,
                            paper_bgcolor="#1f2937",
                            plot_bgcolor="#1f2937",
                            font={'color': "white"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Health Score by Product Type
                        fig = px.bar(
                            x=product_types,
                            y=health_scores,
                            labels={'x': 'Product Type', 'y': 'Health Score'},
                            title="Health Score by Product Type",
                            color=health_scores,
                            color_continuous_scale=['red', 'yellow', 'green']
                        )
                        fig.update_layout(
                            height=350,
                            paper_bgcolor="#1f2937",
                            plot_bgcolor="#1f2937",
                            font={'color': "white"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                # Parameters by Product Type
                st.subheader("Parameters by Product Type")
                
                if product_data['params_by_type']:
                    # Create a dataframe from params_by_type
                    params_data = []
                    for product_type, params in product_data['params_by_type'].items():
                        for param_name, value in params.items():
                            params_data.append({
                                'Product Type': product_type,
                                'Parameter': param_name,
                                'Value': value
                            })
                    
                    df_params = pd.DataFrame(params_data)
                    
                    # Create grouped bar chart
                    fig = px.bar(
                        df_params,
                        x='Parameter',
                        y='Value',
                        color='Product Type',
                        barmode='group',
                        title="Machine Parameters by Product Type"
                    )
                    fig.update_layout(
                        height=400,
                        paper_bgcolor="#1f2937",
                        plot_bgcolor="#1f2937",
                        font={'color': "white"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Tool Wear vs Process Temperature by Product Type
                st.subheader("Tool Wear vs Process Temperature by Product Type")
                
                # Extract data for scatter plot
                scatter_data = []
                for product_type, params in product_data['params_by_type'].items():
                    scatter_data.append({
                        'Product Type': product_type,
                        'Process Temperature': params['process_temperature'],
                        'Tool Wear': params['tool_wear']
                    })
                
                df_scatter = pd.DataFrame(scatter_data)
                
                # Create scatter plot
                fig = px.scatter(
                    df_scatter,
                    x='Process Temperature',
                    y='Tool Wear',
                    color='Product Type',
                    size=[30] * len(scatter_data),
                    title="Tool Wear vs Process Temperature"
                )
                fig.update_layout(
                    height=400,
                    paper_bgcolor="#1f2937",
                    plot_bgcolor="#1f2937",
                    font={'color': "white"}
                )
                st.plotly_chart(fig, use_container_width=True)

# Main function
def main():
    # Initialize session state
    if 'view' not in st.session_state:
        st.session_state.view = "dashboard"
    if 'selected_lathe' not in st.session_state:
        st.session_state.selected_lathe = None
        
    # Navigation
    if st.session_state.view == "dashboard":
        show_dashboard()
    elif st.session_state.view == "lathe_details":
        show_lathe_details()

if __name__ == "__main__":
    main()