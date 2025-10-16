
import os, json, glob, pandas as pd, yaml
from datetime import datetime

def load_cfg():
    with open("configs/config.yaml", "r") as f:
        return yaml.safe_load(f)

def main():
    cfg = load_cfg()
    raw_dir = cfg["ingest"]["raw_dir"]
    bronze_dir = cfg["ingest"]["bronze_dir"]
    os.makedirs(bronze_dir, exist_ok=True)

    records = []
    for path in glob.glob(os.path.join(raw_dir, "*.jsonl")):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    records.append(rec)
                except Exception:
                    pass
    if not records:
        print("No records found. Run data_simulator.py first.")
        return

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.sort_values(["facility_id","sensor_id","timestamp"], inplace=True)

    # partition by facility
    for fac, g in df.groupby("facility_id"):
        out_dir = os.path.join(bronze_dir, f"facility={fac}")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "telemetry.parquet")
        g.to_parquet(out_path, index=False)
    print(f"Wrote Parquet to {bronze_dir}")

if __name__ == "__main__":
    main()
