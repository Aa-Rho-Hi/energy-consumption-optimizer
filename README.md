
# EnergiFlow

**Stack:** AWS IoT (design + optional SAM template), Python, Machine Learning (scikit-learn), Data Visualization (Streamlit), Automation (alerting rules).

This repo demonstrates an IoT-to-ML pipeline for **50 sensors across 10 facilities**, with:
- Near-real-time ingestion (IoT Core → Kinesis/Firehose → S3) — simulated locally here.
- Forecasting models that detect **energy spikes** and suggest optimization actions.
- A dashboard for facility managers (20 users in this case study) to view trends and proactive alerts.
- Automation rules that raise alerts when predicted usage exceeds thresholds.

> The code is fully runnable **locally** (no AWS account required). For cloud deployment, see `infrastructure/sam-template.yaml` as a starting point.

---

## Architecture (Local & Cloud)

```
[Sensors x50]  --> (MQTT JSON)
                    |
                    v
               [AWS IoT Core] -- IoT Rule --> [Kinesis] --> [Firehose] --> [S3 Bronze]
                                                                                                                       +--> [Lambda Predictor] --> [DynamoDB Alerts]
                                                                                     \-> [SNS/Email]
                                [EMR/Glue or Lambda Batch] --> [S3 Silver/Parquet] --> [Athena]
                                                                |
(Local) data_simulator.py --> data/raw/*.jsonl --> ingest_local.py --> data/bronze/*.parquet
                                                                                                                                     +-> train_model.py (per-facility models, saved under artifacts/)
                                                                   +-> predictor_lambda.py (handler-compatible in local mode)
                                                                   +-> serve_api.py (FastAPI, optional)
Dashboard: Streamlit app (dashboard/app.py) reads Parquet and model forecasts
```

---

## Quickstart (Local, no AWS required)

```bash
# 0) Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Generate synthetic telemetry for 50 sensors in 10 facilities
python src/data_simulator.py --sensors 50 --facilities 10 --hours 72

# 2) Ingest JSONL -> Parquet "bronze" store
python src/ingest_local.py

# 3) Train forecasting + spike classifier (per facility)
python src/train_model.py

# 4) Run the dashboard
streamlit run dashboard/app.py

# (Optional) Serve a local API for alerts
uvicorn src.serve_api:app --reload
```

The dashboard will let you pick a facility and see:
- Recent kWh consumption vs. temperature
- Forecast for the next 24 intervals
- Detected/predicted **spikes** and suggested mitigations
- Facility-level KPI rollups

---

## Project Structure

```
energy-consumption-optimizer/
├─ README.md
├─ requirements.txt
├─ LICENSE
├─ configs/
│  └─ config.yaml
├─ data/
│  ├─ raw/           # generated sensor JSONL
│  ├─ bronze/        # ingested Parquet
│  └─ sample/        # tiny sample to explore quickly
├─ artifacts/        # trained models & scalers
├─ src/
│  ├─ data_simulator.py
│  ├─ ingest_local.py
│  ├─ train_model.py
│  ├─ predictor_lambda.py
│  └─ serve_api.py
├─ dashboard/
│  └─ app.py
└─ infrastructure/
   └─ sam-template.yaml  # illustrative AWS SAM template
```

---

## Configuration

Edit `configs/config.yaml`:
- facilities, sensors-per-facility
- ingestion paths
- model training window / forecast horizon
- alert thresholds and actions

---

## Claims & Metrics

This implementation shows how you could achieve:
- **15% reduction in monitoring delays** by streaming ingestion & immediate parquet-ready storage.
- **Up to 15% energy waste reduction** via short-horizon forecasts + automated spike alerts.
- Improved predictive monitoring for **~20 facility managers** via the dashboard.

> Your actual results depend on data quality, sampling frequency, and adherence to recommended actions.

---

## Deployment (AWS, optional)

- Use the **SAM** template to bootstrap: S3 buckets, Kinesis, Firehose, Lambda, DynamoDB, and IoT Topic Rule.
- Replace the Lambda code with `src/predictor_lambda.py` (package with requirements into a Lambda layer or container).
- Point the dashboard (hosted on ECS/Fargate or S3+CloudFront) to an API/Gateway exposing aggregated views.

---

## License
MIT
