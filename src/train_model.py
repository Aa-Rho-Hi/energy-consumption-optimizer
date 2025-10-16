
import os, glob, yaml, pandas as pd, numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib

def load_cfg():
    with open("configs/config.yaml", "r") as f:
        return yaml.safe_load(f)

def feature_engineer(df):
    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    df["lag1"] = df.groupby("sensor_id")["kwh"].shift(1)
    df["lag2"] = df.groupby("sensor_id")["kwh"].shift(2)
    df["lag24"] = df.groupby("sensor_id")["kwh"].shift(24)
    df["rolling_mean_6"] = df.groupby("sensor_id")["kwh"].rolling(6).mean().reset_index(0, drop=True)
    df["rolling_std_6"] = df.groupby("sensor_id")["kwh"].rolling(6).std().reset_index(0, drop=True)
    df.dropna(inplace=True)
    features = ["hour","dayofweek","temp_c","lag1","lag2","lag24","rolling_mean_6","rolling_std_6"]
    return df, features

def main():
    cfg = load_cfg()
    bronze_dir = cfg["ingest"]["bronze_dir"]
    os.makedirs("artifacts", exist_ok=True)

    for fac_path in glob.glob(os.path.join(bronze_dir, "facility=*")):
        fac = fac_path.split("=")[-1]
        df = pd.read_parquet(os.path.join(fac_path, "telemetry.parquet"))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df, feats = feature_engineer(df)

        X = df[feats].values
        y = df["kwh"].values

        pipe = Pipeline([
            ("scaler", StandardScaler(with_mean=False)),  # robust for sparse-like design
            ("rf", RandomForestRegressor(n_estimators=200, random_state=42))
        ])
        pipe.fit(X, y)

        # save model
        joblib.dump({"model": pipe, "features": feats}, f"artifacts/model_{fac}.joblib")
        print(f"Saved artifacts/model_{fac}.joblib")

    print("Training complete.")

if __name__ == "__main__":
    main()
