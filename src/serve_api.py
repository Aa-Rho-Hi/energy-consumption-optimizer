
from fastapi import FastAPI
import pandas as pd, glob, os, joblib
from datetime import datetime, timedelta

app = FastAPI(title="Energy Optimizer API")

def load_facilities():
    facs = []
    for p in glob.glob("data/bronze/facility=*"):
        facs.append(os.path.basename(p).split("=")[-1])
    return sorted(facs)

@app.get("/facilities")
def facilities():
    return {"facilities": load_facilities()}

@app.get("/telemetry/{facility_id}")
def telemetry(facility_id: str, hours: int = 24):
    p = f"data/bronze/facility={facility_id}/telemetry.parquet"
    if not os.path.exists(p):
        return {"records": []}
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(hours=hours)
    df = df[df["timestamp"] >= cutoff]
    return {"records": df.to_dict(orient="records")}
