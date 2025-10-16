
import os, json, joblib, pandas as pd, numpy as np
from datetime import datetime
import glob

THRESHOLD_Z = 2.0

def load_latest_models():
    models = {}
    for p in glob.glob("artifacts/model_*.joblib"):
        fac = os.path.basename(p).split("_")[-1].split(".")[0]
        models[fac] = joblib.load(p)
    return models

def build_features(df, feats):
    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    df["lag1"] = df.groupby("sensor_id")["kwh"].shift(1)
    df["lag2"] = df.groupby("sensor_id")["kwh"].shift(2)
    df["lag24"] = df.groupby("sensor_id")["kwh"].shift(24)
    df["rolling_mean_6"] = df.groupby("sensor_id")["kwh"].rolling(6).mean().reset_index(0, drop=True)
    df["rolling_std_6"] = df.groupby("sensor_id")["kwh"].rolling(6).std().reset_index(0, drop=True)
    df.dropna(inplace=True)
    return df[feats]

def handler(event, context=None):
    # event expects: {"records": [ {timestamp, facility_id, sensor_id, kwh, temp_c}, ... ]}
    data = event["records"]
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    models = load_latest_models()
    alerts = []
    for fac, g in df.groupby("facility_id"):
        if fac not in models:
            continue
        model = models[fac]["model"]
        feats = models[fac]["features"]
        X = build_features(g, feats)
        if X.empty:
            continue
        preds = model.predict(X.values)
        g2 = g.iloc[-len(preds):].copy()
        g2["pred_kwh"] = preds
        # spike detection via z-score on residuals
        resid = g2["kwh"] - g2["pred_kwh"]
        z = (resid - resid.mean()) / (resid.std() + 1e-6)
        g2["spike"] = (z.abs() > THRESHOLD_Z).astype(int)
        for _, row in g2[g2["spike"]==1].iterrows():
            alerts.append({
                "facility_id": row["facility_id"],
                "sensor_id": row["sensor_id"],
                "timestamp": row["timestamp"].isoformat(),
                "kwh": float(row["kwh"]),
                "pred_kwh": float(row["pred_kwh"]),
                "severity": "high" if abs(float(row["kwh"]-row["pred_kwh"]))>1.0 else "medium",
                "action": "Inspect HVAC schedule / baseline; check anomalous load."
            })

    return {"alerts": alerts}

if __name__ == "__main__":
    # quick local test
    sample = {"records":[
        {"timestamp":"2025-10-10T00:00:00","facility_id":"F-001","sensor_id":"F-001-S01","kwh":3.2,"temp_c":26.1}
    ]}
    print(json.dumps(handler(sample), indent=2))
