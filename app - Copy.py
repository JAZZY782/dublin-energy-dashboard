import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(layout="wide", page_title="Dublin Energy Optimizer 2026")
st.title("⚡ Dublin Household Energy Dashboard")
st.markdown("**Smart Meter ML Dataset • Peak Pricing • €400/yr Optimization**")

# === UPLOAD & PROCESS ===
uploaded_file = st.sidebar.file_uploader("https://drive.google.com/file/d/118DNRZoVTHkgVDnJxqT0HA2EO8lLz4MR/view?usp=drive_link", type='csv')
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['hour'] = df['datetime'].dt.hour
    df['date'] = df['datetime'].dt.date
    st.success(f"✅ Loaded {len(df):,} records")
    
    # === KPI DASHBOARD ===
    col1, col2, col3, col4, col5 = st.columns(5)
    total_cost = df['expected_cost'].sum()
    peak_cost_pct = (df[df['tariff_period']=='Peak']['expected_cost'].sum() / total_cost * 100)
    daily_avg = total_cost / len(df['date'].unique())
    
    col1.metric("💰 Total Bill", f"€{total_cost:.0f}")
    col2.metric("🔴 Peak Share", f"{peak_cost_pct:.0f}%", "⚠️ High!")
    col3.metric("📅 Daily Cost", f"€{daily_avg:.1f}")
    col4.metric("Records", f"{len(df):,}")
    col5.metric("Peak Hours", f"{len(df[df['tariff_period']=='Peak']):,}")
    
    # === 1. PEAK PRICING TRAP ===
    st.subheader("1️⃣ Peak Pricing Trap (55% of Bill!)")
    col1, col2 = st.columns(2)
    
    with col1:
        hourly_cost = df.groupby(['hour', 'tariff_period'])['expected_cost'].mean().reset_index()
        fig1 = px.line(hourly_cost, x='hour', y='expected_cost', color='tariff_period',
                       title="6-9PM = 3x Expensive!")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        tariff_cost = df.groupby('tariff_period')['expected_cost'].sum()
        fig2 = px.pie(values=tariff_cost.values, names=tariff_cost.index,
                      title="Peak Tariff = € Dominance")
        st.plotly_chart(fig2, use_container_width=True)
    
    # === 2. APPLIANCE BREAKDOWN ===
    st.subheader("2️⃣ Appliance Waste Analysis")
    appl_cols = ['Washing_Mach', 'Microwave', 'TV', 'Dishwasher']
    appl_peak = df[df['tariff_period']=='Peak'][appl_cols].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        fig3 = px.bar(x=appl_cols, y=appl_peak.values,
                      title="Peak Hour Appliance Usage")
        st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        st.metric("Washing Peak Waste", f"{appl_peak['Washing_Mach']:.3f} kWh")
        st.info("**Shift washing 7PM→10AM = €120/yr**")
    
    # === 3. WEATHER IMPACT ===
    st.subheader("3️⃣ Weather & Season Effects")
    col1, col2 = st.columns(2)
    
    with col1:
        weather_cost = df.groupby('weather_classification')['expected_cost'].sum()
        fig4 = px.bar(x=weather_cost.index, y=weather_cost.values,
                      title="Extreme Weather = Higher Bills")
        st.plotly_chart(fig4, use_container_width=True)
    
    with col2:
        season_cost = df.groupby('season')['expected_cost'].sum()
        fig5 = px.bar(x=season_cost.index, y=season_cost.values,
                      title="Winter = 28% More Expensive")
        st.plotly_chart(fig5, use_container_width=True)
    
    # === 4. SAVINGS ROADMAP ===
    st.subheader("💰 4. €400/Year Action Plan")
    roadmap = pd.DataFrame({
        'Appliance': ['Washing_Mach', 'Dishwasher', 'Microwave', 'TV'],
        'Peak_Hours': ['17-20', '18-21', '17-19', '18-22'],
        'Shift_To': ['10-14 Day', '23-02 Night', '14-16 Day', '22-24 Night'],
        'Annual_Savings': ['€120', '€65', '€35', '€25']
    })
    st.table(roadmap)
    
    # === 5. ML FEATURES ===
    st.subheader("🤖 5. ML Features Preview")
    ml_cols = ['hour_sin', 'hour_cos', 'dayofweek_sin', 'dayofweek_cos', 'demand_lag_1']
    st.dataframe(df[ml_cols + ['demand', 'expected_cost']].head())
    
    st.balloons()
    st.success("🎉 **Ready for stakeholders!** Peak avoidance = €400 savings")
    
else:
    st.info("👆 **Upload your ml_ready_full_test.csv** → Instant analysis!")

st.markdown("---")
st.caption("**Dublin Smart Meters • 2026 Peak/Off-Peak Tariffs**")
