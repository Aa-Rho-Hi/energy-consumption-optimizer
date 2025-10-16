
import streamlit as st
import pandas as pd, numpy as np, glob, os, joblib, yaml
import matplotlib.pyplot as plt

st.set_page_config(page_title="Energy Monitoring & Optimization", layout="wide")

@st.cache_resource
def load_cfg():
    with open("configs/config.yaml", "r") as f:
        return yaml.safe_load(f)

cfg = load_cfg()

st.title("⚡ Energy Consumption Monitoring & Optimization")
st.caption("IoT → ML forecasts → actionable alerts")

# Facility selector
facilities = sorted([p.split("=")[-1] for p in glob.glob("data/bronze/facility=*")])
if not facilities:
    st.warning("No data found. Run the simulator and ingest scripts first.")
    st.stop()

facility = st.selectbox("Facility", facilities, index=max(0, facilities.index(cfg.get("dashboard",{}).get("default_facility","F-001")) if "F-001" in facilities else 0))

# Load data
parquet_path = f"data/bronze/facility={facility}/telemetry.parquet"
df = pd.read_parquet(parquet_path)
df["timestamp"] = pd.to_datetime(df["timestamp"])

# KPIs
total_kwh = df["kwh"].sum()
avg_temp = df["temp_c"].mean()
st.metric("Total kWh (window)", f"{total_kwh:,.0f}")
st.metric("Avg Temperature (°C)", f"{avg_temp:.1f}")

# Recent trend
st.subheader("Recent Consumption (last 48 intervals)")
recent = df.sort_values("timestamp").tail(48)
fig1 = plt.figure()
plt.plot(recent["timestamp"], recent["kwh"])
plt.xlabel("Time"); plt.ylabel("kWh")
plt.title(f"Facility {facility} — Recent kWh")
st.pyplot(fig1)

# Load model
model_path = f"artifacts/model_{facility}.joblib"
if not os.path.exists(model_path):
    st.error("Model not found. Run train_model.py")
    st.stop()
bundle = joblib.load(model_path)
model, feats = bundle["model"], bundle["features"]

# Feature engineering (same as training)
g = df.copy()
g["hour"] = g["timestamp"].dt.hour
g["dayofweek"] = g["timestamp"].dt.dayofweek
g["lag1"] = g.groupby("sensor_id")["kwh"].shift(1)
g["lag2"] = g.groupby("sensor_id")["kwh"].shift(2)
g["lag24"] = g.groupby("sensor_id")["kwh"].shift(24)
g["rolling_mean_6"] = g.groupby("sensor_id")["kwh"].rolling(6).mean().reset_index(0, drop=True)
g["rolling_std_6"] = g.groupby("sensor_id")["kwh"].rolling(6).std().reset_index(0, drop=True)
g.dropna(inplace=True)

X = g[feats].values
g["pred_kwh"] = model.predict(X)

resid = g["kwh"] - g["pred_kwh"]
z = (resid - resid.mean()) / (resid.std() + 1e-6)
g["spike"] = (z.abs() > cfg["modeling"]["spike_threshold_std"]).astype(int)

st.subheader("Forecast vs Actual (last 48 intervals)")
show = g.sort_values("timestamp").tail(48)
fig2 = plt.figure()
plt.plot(show["timestamp"], show["kwh"], label="actual")
plt.plot(show["timestamp"], show["pred_kwh"], label="forecast")
plt.xlabel("Time"); plt.ylabel("kWh"); plt.title("Actual vs Forecast")
plt.legend()
st.pyplot(fig2)

spikes = show[show["spike"]==1][["timestamp","sensor_id","kwh","pred_kwh"]]
st.subheader("Detected Spikes")
st.dataframe(spikes)

st.subheader("Suggested Actions")
if spikes.empty:
    st.success("No spikes detected in the recent window. 👍 Consider maintaining current schedules.")
else:
    st.warning("Spikes detected. Consider:")
    st.markdown("- Verify HVAC schedules and setpoints during detected intervals.")
    st.markdown("- Investigate equipment left running after hours.")
    st.markdown("- Check for simultaneous high-load processes and reschedule if possible.")
