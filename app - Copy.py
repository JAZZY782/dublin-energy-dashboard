import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(layout="wide")

@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['hour'] = df['datetime'].dt.hour
    df['date'] = df['datetime'].dt.date
    return df

st.title("🏠 Dublin Household Energy Dashboard")
st.markdown("*880K smart meter records • 30min intervals • Ireland tariffs*")

# File upload
uploaded_file = st.sidebar.file_uploader("📁 Upload ml_ready_full_test.csv", type='csv')
if uploaded_file:
    df = load_data(uploaded_file)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", f"{len(df):,}")
    col2.metric("Avg Demand", f"{df['demand'].mean():.3f}kW")
    col3.metric("Peak Demand", f"{df['demand'].max():.3f}kW")
    col4.metric("Avg Cost/Day", f"€{df['expected_cost'].sum()/len(df['date'].unique()):.2f}")
    
    # Charts row 1
    col1, col2 = st.columns(2)
    with col1:
        hourly = df.groupby(['hour', 'tariff_period'])['demand'].mean().reset_index()
        fig1 = px.line(hourly, x='hour', y='demand', color='tariff_period', 
                      title="Hourly Demand Pattern")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        appliances = ['Washing_Mach', 'Microwave', 'TV', 'Dishwasher']
        app_avg = df[appliances].mean()
        fig2 = px.pie(values=app_avg.values, names=app_avg.index, title="Appliance Usage")
        st.plotly_chart(fig2, use_container_width=True)
    
    # Charts row 2  
    col3, col4 = st.columns(2)
    with col3:
        daily_cost = df.groupby('date')['expected_cost'].sum().reset_index()
        fig3 = px.line(daily_cost, x='date', y='expected_cost', title="Daily Cost")
        st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        holiday = df.groupby(['is_holiday', 'hour'])['demand'].mean().unstack()
        fig4 = px.line(holiday, title="Holiday vs Normal Demand")
        st.plotly_chart(fig4, use_container_width=True)
        
else:
    st.info("👆 **Upload your CSV to see interactive dashboard!**")

st.markdown("---")
st.caption("**Dublin Smart Meters • Built with Streamlit • 2026**")
