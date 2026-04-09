import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import gdown

st.set_page_config(
    page_title="Dublin Household Energy Dashboard",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Dublin Household Energy Cost & Consumption Dashboard")
st.caption("Smart meter analysis of demand, tariff exposure, appliance timing, and load-shifting opportunities")

FILE_ID = "118DNRZoVTHkgVDnJxqT0HA2EO8lLz4MR"
LOCAL_FILE = "ml_ready_full_test.csv"


@st.cache_data(show_spinner="Downloading and loading dataset...")
def load_data():
    url = f"https://drive.google.com/uc?id={FILE_ID}"

    if not os.path.exists(LOCAL_FILE):
        gdown.download(url, LOCAL_FILE, quiet=False)

    df = pd.read_csv(LOCAL_FILE, low_memory=False)

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    elif "datetime" in df.columns:
        df["date"] = df["datetime"].dt.date
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    text_cols = [
        "weekday_type",
        "season",
        "holiday",
        "holiday_name",
        "weather_type",
        "weather_classification",
        "tariff_period"
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    numeric_cols = [
        "demand",
        "temp",
        "demand_lag_1",
        "hour",
        "dayofweek",
        "hour_sin",
        "hour_cos",
        "dayofweek_sin",
        "dayofweek_cos",
        "Washing_Mach",
        "Microwave",
        "TV",
        "Dishwasher",
        "sum_appliances",
        "unallocated",
        "tariff_price",
        "expected_cost"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    bool_like_cols = ["is_weekend", "is_holiday"]
    for col in bool_like_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.lower()
                .isin(["true", "1", "yes"])
            )

    if "hour" in df.columns:
        df["hour"] = df["hour"].fillna(-1).astype(int)

    return df


df = load_data()

if df.empty:
    st.error("The dataset loaded successfully but is empty.")
    st.stop()

st.sidebar.header("Filters")

def safe_options(frame, column):
    if column not in frame.columns:
        return []
    return sorted(frame[column].dropna().astype(str).unique().tolist())

tariff_options = safe_options(df, "tariff_period")
weather_options = safe_options(df, "weather_classification")
weekday_options = safe_options(df, "weekday_type")

tariff_filter = st.sidebar.multiselect(
    "Tariff Period",
    tariff_options,
    default=tariff_options
)

weather_filter = st.sidebar.multiselect(
    "Weather Classification",
    weather_options,
    default=weather_options
)

weekday_filter = st.sidebar.multiselect(
    "Weekday Type",
    weekday_options,
    default=weekday_options
)

filtered_df = df.copy()

if "tariff_period" in filtered_df.columns and tariff_filter:
    filtered_df = filtered_df[filtered_df["tariff_period"].isin(tariff_filter)]

if "weather_classification" in filtered_df.columns and weather_filter:
    filtered_df = filtered_df[filtered_df["weather_classification"].isin(weather_filter)]

if "weekday_type" in filtered_df.columns and weekday_filter:
    filtered_df = filtered_df[filtered_df["weekday_type"].isin(weekday_filter)]

if filtered_df.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

total_demand = filtered_df["demand"].sum() if "demand" in filtered_df.columns else 0
total_cost = filtered_df["expected_cost"].sum() if "expected_cost" in filtered_df.columns else 0

if "date" in filtered_df.columns and "expected_cost" in filtered_df.columns:
    avg_daily_cost = filtered_df.groupby("date")["expected_cost"].sum().mean()
else:
    avg_daily_cost = 0

if "tariff_period" in filtered_df.columns and "expected_cost" in filtered_df.columns and total_cost > 0:
    peak_cost_share = (
        filtered_df.loc[filtered_df["tariff_period"] == "Peak", "expected_cost"].sum() / total_cost
    ) * 100
else:
    peak_cost_share = 0

if "unallocated" in filtered_df.columns and "demand" in filtered_df.columns and total_demand > 0:
    unallocated_share = (filtered_df["unallocated"].sum() / total_demand) * 100
else:
    unallocated_share = 0

records = len(filtered_df)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Demand", f"{total_demand:,.0f}")
c2.metric("Total Estimated Cost", f"€{total_cost:,.0f}")
c3.metric("Avg Daily Cost", f"€{avg_daily_cost:,.2f}")
c4.metric("Peak Cost Share", f"{peak_cost_share:.1f}%")
c5.metric("Unallocated Share", f"{unallocated_share:.1f}%")

st.success(f"Loaded {records:,} filtered records")

st.subheader("1. Tariff & Cost Exposure")

if {"tariff_period", "expected_cost"}.issubset(filtered_df.columns):
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
    fig_tariff.update_layout(
        xaxis_title="Tariff Period",
        yaxis_title="Total Cost (€)"
    )
    st.plotly_chart(fig_tariff, use_container_width=True)

    st.info(
        "This chart shows how the total bill is distributed across tariff periods. "
        "Peak periods may contain fewer hours, but they still create strong cost pressure when demand overlaps with high prices."
    )

if {"hour", "demand", "expected_cost"}.issubset(filtered_df.columns):
    hourly_profile = (
        filtered_df.groupby("hour", as_index=False)
        .agg(
            avg_demand=("demand", "mean"),
            total_cost=("expected_cost", "sum")
        )
        .sort_values("hour")
    )

    fig_hourly = go.Figure()
    fig_hourly.add_trace(
        go.Scatter(
            x=hourly_profile["hour"],
            y=hourly_profile["avg_demand"],
            mode="lines+markers",
            name="Average Demand"
        )
    )
    fig_hourly.add_trace(
        go.Scatter(
            x=hourly_profile["hour"],
            y=hourly_profile["total_cost"],
            mode="lines+markers",
            name="Total Cost",
            yaxis="y2"
        )
    )
    fig_hourly.update_layout(
        title="Hourly Demand and Cost Profile",
        xaxis=dict(title="Hour of Day"),
        yaxis=dict(title="Average Demand"),
        yaxis2=dict(title="Total Cost (€)", overlaying="y", side="right"),
        legend=dict(orientation="h")
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

    peak_hour = hourly_profile.loc[hourly_profile["total_cost"].idxmax(), "hour"]
    st.markdown(
        f"**Key takeaway:** The strongest cost pressure occurs around **hour {int(peak_hour)}**, "
        "where higher demand and more expensive tariff exposure overlap."
    )

st.subheader("2. Appliance Usage Patterns")

appliance_cols = ["Washing_Mach", "Microwave", "TV", "Dishwasher"]
available_appliance_cols = [col for col in appliance_cols if col in filtered_df.columns]

if available_appliance_cols:
    appliance_totals = pd.DataFrame({
        "Appliance": available_appliance_cols,
        "Total_Usage": [filtered_df[col].sum() for col in available_appliance_cols]
    })

    fig_appliance_total = px.bar(
        appliance_totals,
        x="Appliance",
        y="Total_Usage",
        text_auto=".2s",
        title="Total Tracked Appliance Usage"
    )
    fig_appliance_total.update_layout(
        xaxis_title="Appliance",
        yaxis_title="Total Usage"
    )
    st.plotly_chart(fig_appliance_total, use_container_width=True)

if {"tariff_period"}.issubset(filtered_df.columns) and available_appliance_cols:
    peak_df = filtered_df[filtered_df["tariff_period"] == "Peak"].copy()

    appliance_peak = pd.DataFrame({
        "Appliance": available_appliance_cols,
        "Peak_Usage": [peak_df[col].sum() for col in available_appliance_cols]
    })

    fig_appliance_peak = px.bar(
        appliance_peak,
        x="Appliance",
        y="Peak_Usage",
        text_auto=".2s",
        title="Appliance Usage During Peak Tariff Hours"
    )
    fig_appliance_peak.update_layout(
        xaxis_title="Appliance",
        yaxis_title="Peak-Hour Usage"
    )
    st.plotly_chart(fig_appliance_peak, use_container_width=True)

    st.warning(
        "Interpretation note: This chart shows peak-hour appliance usage, not total appliance usage. "
        "An appliance can be low during peak hours but still be high overall."
    )

if {"hour"}.issubset(filtered_df.columns) and available_appliance_cols:
    heatmap_data = (
        filtered_df.groupby("hour")[available_appliance_cols]
        .mean()
        .reset_index()
        .sort_values("hour")
    )
    heatmap_melt = heatmap_data.melt(
        id_vars="hour",
        var_name="Appliance",
        value_name="Avg Usage"
    )

    fig_heatmap = px.density_heatmap(
        heatmap_melt,
        x="hour",
        y="Appliance",
        z="Avg Usage",
        histfunc="avg",
        title="Average Appliance Usage by Hour"
    )
    fig_heatmap.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Appliance"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

if {"sum_appliances", "unallocated"}.issubset(filtered_df.columns):
    tracked_sum = filtered_df["sum_appliances"].sum()
    unallocated_sum = filtered_df["unallocated"].sum()

    unallocated_df = pd.DataFrame({
        "Category": ["Tracked Appliances", "Unallocated Load"],
        "Value": [tracked_sum, unallocated_sum]
    })

    fig_unallocated = px.pie(
        unallocated_df,
        names="Category",
        values="Value",
        title="Tracked vs Unallocated Household Load"
    )
    st.plotly_chart(fig_unallocated, use_container_width=True)

    st.info(
        "A large share of demand is not explained by the tracked appliance columns. "
        "This likely reflects other household loads such as lighting, refrigeration, cooking, heating, or standby consumption."
    )

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
    "Savings Potential": [
        "Low",
        "High",
        "Medium",
        "Low-Medium"
    ]
})
st.dataframe(shift_plan, use_container_width=True)
st.caption("Savings potential is shown as a directional recommendation based on tariff timing patterns in the dataset.")

st.subheader("4. External Drivers")

if {"weather_classification", "demand", "expected_cost"}.issubset(filtered_df.columns):
    weather_summary = (
        filtered_df.groupby("weather_classification", as_index=False)
        .agg(
            avg_demand=("demand", "mean"),
            total_cost=("expected_cost", "sum"),
            records=("demand", "count")
        )
        .sort_values("avg_demand", ascending=False)
    )

    fig_weather = px.bar(
        weather_summary,
        x="weather_classification",
        y="avg_demand",
        text_auto=".3f",
        title="Average Demand by Weather Classification"
    )
    fig_weather.update_layout(
        xaxis_title="Weather Classification",
        yaxis_title="Average Demand"
    )
    st.plotly_chart(fig_weather, use_container_width=True)

    st.warning(
        "Weather insights should be interpreted cautiously if some weather categories contain relatively few records."
    )

if {"weekday_type", "demand", "expected_cost"}.issubset(filtered_df.columns):
    weekday_summary = (
        filtered_df.groupby("weekday_type", as_index=False)
        .agg(
            avg_demand=("demand", "mean"),
            total_cost=("expected_cost", "sum")
        )
    )

    fig_weekday = px.bar(
        weekday_summary,
        x="weekday_type",
        y="avg_demand",
        color="weekday_type",
        title="Average Demand: Weekday vs Weekend"
    )
    fig_weekday.update_layout(
        xaxis_title="Weekday Type",
        yaxis_title="Average Demand",
        showlegend=False
    )
    st.plotly_chart(fig_weekday, use_container_width=True)

    st.info(
        "If weekday and weekend values are close, it suggests that hour-of-day behavior may be a stronger cost driver than day type alone."
    )

if {"temp", "demand"}.issubset(filtered_df.columns):
    sample_size = min(20000, len(filtered_df))
    sample_df = filtered_df.sample(sample_size, random_state=42)

    fig_temp = px.scatter(
        sample_df,
        x="temp",
        y="demand",
        opacity=0.3,
        title="Temperature vs Demand (Sampled)"
    )
    fig_temp.update_layout(
        xaxis_title="Temperature",
        yaxis_title="Demand"
    )
    st.plotly_chart(fig_temp, use_container_width=True)

st.subheader("5. ML Readiness Preview")

feature_cols = [
    "hour",
    "dayofweek",
    "is_weekend",
    "temp",
    "demand_lag_1",
    "hour_sin",
    "hour_cos",
    "dayofweek_sin",
    "dayofweek_cos",
    "tariff_price",
    "expected_cost"
]
available_feature_cols = [c for c in feature_cols if c in filtered_df.columns]

if available_feature_cols:
    st.dataframe(filtered_df[available_feature_cols].head(10), use_container_width=True)

corr_cols = [
    "demand",
    "temp",
    "demand_lag_1",
    "hour",
    "hour_sin",
    "hour_cos",
    "dayofweek_sin",
    "dayofweek_cos",
    "tariff_price",
    "expected_cost",
    "Washing_Mach",
    "Microwave",
    "TV",
    "Dishwasher"
]
corr_cols = [c for c in corr_cols if c in filtered_df.columns]

if len(corr_cols) >= 2:
    corr = filtered_df[corr_cols].corr(numeric_only=True)

    fig_corr = px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        title="Feature Correlation Heatmap"
    )
    st.plotly_chart(fig_corr, use_container_width=True)

st.success(
    "The dataset includes time features, appliance variables, lagged demand, temperature, and tariff price, "
    "which makes it suitable for demand forecasting, cost prediction, and peak-period classification."
)

st.subheader("6. Final Summary")
st.markdown("""
### Key Insights
- Evening demand creates the strongest cost pressure.
- Peak-hour inefficiency is driven more by timing than total usage.
- Microwaves, TVs, and dishwashers contribute more to peak-hour pressure than washing machines.
- Most demand remains unallocated, indicating hidden household loads.
- The dataset is suitable for future forecasting and optimization models.
""")
