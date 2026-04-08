import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dublin Household Energy Dashboard", page_icon="⚡", layout="wide")

st.title("⚡ Dublin Household Energy Cost & Consumption Dashboard")
st.caption("Smart meter analysis of demand, tariff exposure, appliance timing, and load-shifting opportunities")

@st.cache_data
def load_data(path):
    df = pd.read_csv("https://drive.google.com/file/d/118DNRZoVTHkgVDnJxqT0HA2EO8lLz4MR/view?usp=drive_link", low_memory=False)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    text_cols = ["weekday_type", "season", "holiday", "holiday_name",
                 "weather_type", "weather_classification", "tariff_period"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    numeric_cols = [
        "demand", "temp", "demand_lag_1", "hour", "dayofweek",
        "hour_sin", "hour_cos", "dayofweek_sin", "dayofweek_cos",
        "Washing_Mach", "Microwave", "TV", "Dishwasher",
        "sum_appliances", "unallocated", "tariff_price", "expected_cost"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "is_weekend" in df.columns:
        df["is_weekend"] = df["is_weekend"].astype(str).str.lower().isin(["true", "1", "yes"])
    if "is_holiday" in df.columns:
        df["is_holiday"] = df["is_holiday"].astype(str).str.lower().isin(["true", "1", "yes"])

    return df

df = load_data("ml_ready_full_test.csv")

st.sidebar.header("Filters")

tariff_filter = st.sidebar.multiselect(
    "Tariff Period",
    sorted(df["tariff_period"].dropna().unique()),
    default=sorted(df["tariff_period"].dropna().unique())
)

weather_filter = st.sidebar.multiselect(
    "Weather Classification",
    sorted(df["weather_classification"].dropna().unique()),
    default=sorted(df["weather_classification"].dropna().unique())
)

weekday_filter = st.sidebar.multiselect(
    "Weekday Type",
    sorted(df["weekday_type"].dropna().unique()),
    default=sorted(df["weekday_type"].dropna().unique())
)

filtered_df = df[
    df["tariff_period"].isin(tariff_filter) &
    df["weather_classification"].isin(weather_filter) &
    df["weekday_type"].isin(weekday_filter)
].copy()

total_demand = filtered_df["demand"].sum()
total_cost = filtered_df["expected_cost"].sum()
avg_daily_cost = filtered_df.groupby("date")["expected_cost"].sum().mean()

peak_cost_share = (
    filtered_df.loc[filtered_df["tariff_period"] == "Peak", "expected_cost"].sum()
    / filtered_df["expected_cost"].sum()
) * 100 if filtered_df["expected_cost"].sum() > 0 else 0

unallocated_share = (
    filtered_df["unallocated"].sum() / filtered_df["demand"].sum()
) * 100 if filtered_df["demand"].sum() > 0 else 0

records = len(filtered_df)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Demand", f"{total_demand:,.0f}")
c2.metric("Total Estimated Cost", f"€{total_cost:,.0f}")
c3.metric("Avg Daily Cost", f"€{avg_daily_cost:,.2f}")
c4.metric("Peak Cost Share", f"{peak_cost_share:.1f}%")
c5.metric("Unallocated Share", f"{unallocated_share:.1f}%")

st.success(f"Loaded {records:,} filtered records")

st.subheader("1. Tariff & Cost Exposure")

tariff_cost = (
    filtered_df.groupby("tariff_period", as_index=False)["expected_cost"]
    .sum()
    .sort_values("expected_cost", ascending=False)
)

fig_tariff = px.bar(
    tariff_cost,
    x="tariff_period",
    y="expected_cost",
    text_auto=".2s",
    title="Total Electricity Cost by Tariff Period"
)
st.plotly_chart(fig_tariff, use_container_width=True)

hourly_profile = (
    filtered_df.groupby("hour", as_index=False)
    .agg(avg_demand=("demand", "mean"),
         total_cost=("expected_cost", "sum"))
)

fig_hourly = go.Figure()
fig_hourly.add_trace(go.Scatter(x=hourly_profile["hour"], y=hourly_profile["avg_demand"],
                                mode="lines+markers", name="Average Demand"))
fig_hourly.add_trace(go.Scatter(x=hourly_profile["hour"], y=hourly_profile["total_cost"],
                                mode="lines+markers", name="Total Cost", yaxis="y2"))
fig_hourly.update_layout(
    title="Hourly Demand and Cost Profile",
    xaxis=dict(title="Hour of Day"),
    yaxis=dict(title="Average Demand"),
    yaxis2=dict(title="Total Cost (€)", overlaying="y", side="right")
)
st.plotly_chart(fig_hourly, use_container_width=True)

st.subheader("2. Appliance Usage Patterns")

appliance_cols = ["Washing_Mach", "Microwave", "TV", "Dishwasher"]

appliance_totals = pd.DataFrame({
    "Appliance": appliance_cols,
    "Total_Usage": [filtered_df[col].sum() for col in appliance_cols]
})
fig_appliance_total = px.bar(appliance_totals, x="Appliance", y="Total_Usage",
                             text_auto=".2s", title="Total Tracked Appliance Usage")
st.plotly_chart(fig_appliance_total, use_container_width=True)

peak_df = filtered_df[filtered_df["tariff_period"] == "Peak"].copy()
appliance_peak = pd.DataFrame({
    "Appliance": appliance_cols,
    "Peak_Usage": [peak_df[col].sum() for col in appliance_cols]
})
fig_appliance_peak = px.bar(appliance_peak, x="Appliance", y="Peak_Usage",
                            text_auto=".2s", title="Appliance Usage During Peak Tariff Hours")
st.plotly_chart(fig_appliance_peak, use_container_width=True)

heatmap_data = filtered_df.groupby("hour")[appliance_cols].mean().reset_index()
heatmap_melt = heatmap_data.melt(id_vars="hour", var_name="Appliance", value_name="Avg Usage")
fig_heatmap = px.density_heatmap(
    heatmap_melt, x="hour", y="Appliance", z="Avg Usage",
    histfunc="avg", title="Average Appliance Usage by Hour"
)
st.plotly_chart(fig_heatmap, use_container_width=True)

tracked_sum = filtered_df["sum_appliances"].sum()
unallocated_sum = filtered_df["unallocated"].sum()
unallocated_df = pd.DataFrame({
    "Category": ["Tracked Appliances", "Unallocated Load"],
    "Value": [tracked_sum, unallocated_sum]
})
fig_unallocated = px.pie(unallocated_df, names="Category", values="Value",
                         title="Tracked vs Unallocated Household Load")
st.plotly_chart(fig_unallocated, use_container_width=True)

st.subheader("3. Load Shifting Opportunities")
shift_plan = pd.DataFrame({
    "Appliance": ["Washing_Mach", "Dishwasher", "Microwave", "TV"],
    "Current Peak Behaviour": [
        "Mostly outside peak",
        "Often overlaps with evening",
        "Strong evening overlap",
        "Strong evening overlap"
    ],
    "Suggested Shift Window": [
        "Already efficient",
        "After 22:00",
        "14:00-16:00 where possible",
        "Reduce during 18:00-22:00"
    ],
    "Savings Potential": ["Low", "High", "Medium", "Low-Medium"]
})
st.dataframe(shift_plan, use_container_width=True)

st.subheader("4. External Drivers")

weather_summary = (
    filtered_df.groupby("weather_classification", as_index=False)
    .agg(avg_demand=("demand", "mean"),
         total_cost=("expected_cost", "sum"),
         records=("demand", "count"))
)
fig_weather = px.bar(weather_summary, x="weather_classification", y="avg_demand",
                     text_auto=".3f", title="Average Demand by Weather Classification")
st.plotly_chart(fig_weather, use_container_width=True)

weekday_summary = (
    filtered_df.groupby("weekday_type", as_index=False)
    .agg(avg_demand=("demand", "mean"),
         total_cost=("expected_cost", "sum"))
)
fig_weekday = px.bar(weekday_summary, x="weekday_type", y="avg_demand",
                     color="weekday_type", title="Average Demand: Weekday vs Weekend")
st.plotly_chart(fig_weekday, use_container_width=True)

sample_df = filtered_df.sample(min(20000, len(filtered_df)), random_state=42)
fig_temp = px.scatter(sample_df, x="temp", y="demand", opacity=0.3,
                      title="Temperature vs Demand (Sampled)")
st.plotly_chart(fig_temp, use_container_width=True)

st.subheader("5. ML Readiness Preview")

feature_cols = [
    "hour", "dayofweek", "is_weekend", "temp", "demand_lag_1",
    "hour_sin", "hour_cos", "dayofweek_sin", "dayofweek_cos",
    "tariff_price", "expected_cost"
]
available_feature_cols = [c for c in feature_cols if c in filtered_df.columns]
st.dataframe(filtered_df[available_feature_cols].head(10), use_container_width=True)

corr_cols = [
    "demand", "temp", "demand_lag_1", "hour", "hour_sin", "hour_cos",
    "dayofweek_sin", "dayofweek_cos", "tariff_price", "expected_cost",
    "Washing_Mach", "Microwave", "TV", "Dishwasher"
]
corr_cols = [c for c in corr_cols if c in filtered_df.columns]
corr = filtered_df[corr_cols].corr(numeric_only=True)
fig_corr = px.imshow(corr, text_auto=".2f", aspect="auto", title="Feature Correlation Heatmap")
st.plotly_chart(fig_corr, use_container_width=True)

st.subheader("6. Final Summary")
st.markdown("""
### Key Insights
- Evening demand creates the strongest cost pressure.
- Peak-hour inefficiency is driven more by timing than total usage.
- Microwaves, TVs, and dishwashers contribute more to peak-hour pressure than washing machines.
- Most demand remains unallocated, indicating hidden household loads.
- The dataset is suitable for future forecasting and optimization models.
""")


