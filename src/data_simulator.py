
import argparse, os, json, random, time
from datetime import datetime, timedelta
import numpy as np
import yaml

def load_cfg():
    with open("configs/config.yaml", "r") as f:
        return yaml.safe_load(f)

def gen_series(base_kwh, temp_c, t):
    # Diurnal pattern + noise + temp sensitivity
    hour = t.hour
    diurnal = 0.6 + 0.4*np.sin((hour/24)*2*np.pi)
    temp_factor = 1 + 0.02*max(0, temp_c-22)  # >22C increases usage slightly
    noise = np.random.normal(0, 0.05)
    return max(0.1, base_kwh * diurnal * temp_factor * (1+noise))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sensors", type=int, default=50)
    p.add_argument("--facilities", type=int, default=10)
    p.add_argument("--hours", type=int, default=72)
    args = p.parse_args()

    cfg = load_cfg()
    raw_dir = cfg["ingest"]["raw_dir"]
    os.makedirs(raw_dir, exist_ok=True)

    facilities = [f"F-{i:03d}" for i in range(1, args.facilities+1)]
    sensors_per_fac = max(1, args.sensors // args.facilities)

    start = datetime.utcnow() - timedelta(hours=args.hours)
    steps = args.hours

    for fac in facilities:
        for s in range(1, sensors_per_fac+1):
            sid = f"{fac}-S{s:02d}"
            base_kwh = random.uniform(1.0, 5.0)
            # Write one JSONL per sensor
            path = os.path.join(raw_dir, f"{sid}.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                t = start
                for _ in range(steps):
                    temp_c = random.uniform(18, 32)
                    kwh = gen_series(base_kwh, temp_c, t)
                    # occasional spike
                    if random.random() < 0.03:
                        kwh *= random.uniform(1.5, 2.5)
                    rec = {
                        "timestamp": t.isoformat(),
                        "facility_id": fac,
                        "sensor_id": sid,
                        "kwh": round(kwh, 3),
                        "temp_c": round(temp_c, 2)
                    }
                    f.write(json.dumps(rec) + "\n")
                    t += timedelta(hours=1)

    print(f"Wrote JSONL files to {raw_dir}")

if __name__ == "__main__":
    main()
