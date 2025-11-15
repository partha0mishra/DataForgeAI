# Model Factory with MLflow

Enterprise ML platform for model training, experimentation, registry, and serving with full lifecycle management.

## Features

- **Experiment Tracking**: Track all ML experiments with MLflow
- **Hyperparameter Tuning**: Automated optimization with Optuna
- **Model Registry**: Version control for ML models
- **Model Serving**: Real-time prediction API
- **Stage Management**: Development → Staging → Production workflow
- **Model Lineage**: Track data and code lineage
- **Multiple Frameworks**: Support for scikit-learn, XGBoost, LightGBM
- **Batch & Real-time**: Both batch and online predictions
- **Performance Monitoring**: Track prediction latency and throughput

## Quick Start

### 1. Install Dependencies

```bash
cd accelerators/05-model-factory
pip install -r requirements.txt
```

### 2. Start MLflow Server (Optional)

```bash
mlflow server --host 0.0.0.0 --port 5000
```

### 3. Run Complete Example

```bash
python examples/ml_lifecycle_example.py
```

This demonstrates:
- Training multiple models
- Hyperparameter tuning
- Experiment tracking
- Model registration
- Stage promotion (Staging → Production)
- Real-time serving

### 4. Start API Server

```bash
cd src
uvicorn api.main:app --reload --port 8004
```

API will be available at: http://localhost:8004

## Architecture

### Components

```
Model Factory
├── Training           # Model training with tuning
├── Experiment Tracker # MLflow experiment logging
├── Model Registry    # Version control and lifecycle
└── Model Server      # Real-time serving
```

### ML Lifecycle Flow

```
Data → Train → Tune → Track → Register → Stage → Serve → Monitor
         ↓       ↓       ↓        ↓        ↓       ↓        ↓
      Trainer  Optuna MLflow  Registry  Staging  API  Prometheus
```

## Core Components

### 1. Experiment Tracker (`training/experiment_tracker.py`)

Track ML experiments with MLflow:

```python
from training.experiment_tracker import ExperimentTracker

tracker = ExperimentTracker(
    experiment_name="customer_churn",
    tracking_uri="http://mlflow:5000"
)

# Start run
with tracker.start_run(run_name="xgboost_v1"):
    # Log parameters
    tracker.log_params({
        "n_estimators": 100,
        "max_depth": 5,
        "learning_rate": 0.1
    })

    # Train model
    model.fit(X_train, y_train)

    # Log metrics
    tracker.log_metrics({
        "accuracy": 0.92,
        "f1_score": 0.89,
        "roc_auc": 0.94
    })

    # Log model
    tracker.log_model(model, "model")

# Find best run
best_run = tracker.get_best_run("f1_score", mode="max")
print(f"Best F1: {best_run.metrics['f1_score']}")
```

### 2. Model Trainer (`training/model_trainer.py`)

Train with hyperparameter tuning:

```python
from training.model_trainer import ModelTrainer, TrainingConfig
from xgboost import XGBClassifier

trainer = ModelTrainer(
    config=TrainingConfig(
        task_type="classification",
        metric="f1",
        cv_folds=5,
        n_trials=50  # Optuna trials
    )
)

# Define parameter space
param_space = {
    "n_estimators": ("int", 50, 300),
    "max_depth": ("int", 3, 10),
    "learning_rate": ("float", 0.01, 0.3),
    "subsample": ("float", 0.6, 1.0)
}

# Train with tuning
result = trainer.train_with_tuning(
    X=X_train,
    y=y_train,
    model_class=XGBClassifier,
    param_space=param_space
)

print(f"Best params: {result.best_params}")
print(f"Test F1: {result.test_score:.3f}")
print(f"CV: {result.cv_mean:.3f} ± {result.cv_std:.3f}")
```

### 3. Model Registry (`registry/model_registry.py`)

Manage model versions and lifecycle:

```python
from registry.model_registry import ModelRegistry, ModelStage

registry = ModelRegistry(tracking_uri="http://mlflow:5000")

# Register model from run
version = registry.register_model(
    model_uri="runs:/abc123/model",
    name="customer_churn_predictor",
    description="XGBoost model for churn prediction",
    tags={"framework": "xgboost", "task": "classification"}
)

# Promote to staging
registry.transition_stage(
    name="customer_churn_predictor",
    version=version,
    stage=ModelStage.STAGING
)

# Test in staging, then promote to production
registry.promote_to_production(
    name="customer_churn_predictor",
    version=version
)

# Get production model
prod_model = registry.get_production_model("customer_churn_predictor")
print(f"Production: v{prod_model.version}")
```

### 4. Model Server (`serving/model_server.py`)

Serve models for predictions:

```python
from serving.model_server import ModelServer

server = ModelServer(registry=model_registry, cache_size=10)

# Load production model
server.load_model("customer_churn_predictor", stage="Production")

# Single prediction
response = server.predict(
    model_name="customer_churn_predictor",
    model_stage="Production",
    features={
        "age": 35,
        "tenure_months": 24,
        "monthly_charges": 79.99,
        "total_charges": 1919.76
    }
)

print(f"Prediction: {response.predictions[0]}")
print(f"Latency: {response.latency_ms:.2f} ms")

# Batch prediction
batch_response = server.predict(
    model_name="customer_churn_predictor",
    instances=[
        {"age": 35, "tenure_months": 24, ...},
        {"age": 42, "tenure_months": 48, ...},
    ]
)

print(f"Predictions: {batch_response.predictions}")
```

## API Endpoints

### Model Registry

**Register Model**
```bash
curl -X POST "http://localhost:8004/registry/models" \
  -H "Content-Type: application/json" \
  -d '{
    "model_uri": "runs:/abc123/model",
    "name": "customer_churn_predictor",
    "description": "XGBoost churn model",
    "tags": {"framework": "xgboost"}
  }'
```

**List Models**
```bash
curl "http://localhost:8004/registry/models"
```

**Get Model Version**
```bash
curl "http://localhost:8004/registry/models/{name}/versions/{version}"
```

**Transition Stage**
```bash
curl -X POST "http://localhost:8004/registry/models/{name}/versions/{version}/stage" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "Production",
    "archive_existing": true
  }'
```

**Promote to Production**
```bash
curl -X POST "http://localhost:8004/registry/models/{name}/versions/{version}/promote"
```

**Get Production Model**
```bash
curl "http://localhost:8004/registry/models/{name}/production"
```

Response:
```json
{
  "name": "customer_churn_predictor",
  "version": "3",
  "stage": "Production",
  "metrics": {
    "accuracy": 0.92,
    "f1_score": 0.89,
    "roc_auc": 0.94
  },
  "created_at": "2025-11-15T10:30:00Z"
}
```

**Get Model Lineage**
```bash
curl "http://localhost:8004/registry/models/{name}/versions/{version}/lineage"
```

### Model Serving

**Load Model**
```bash
curl -X POST "http://localhost:8004/serving/load" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_churn_predictor",
    "stage": "Production"
  }'
```

**Make Prediction**
```bash
curl -X POST "http://localhost:8004/serving/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "customer_churn_predictor",
    "model_stage": "Production",
    "features": {
      "age": 35,
      "tenure_months": 24,
      "monthly_charges": 79.99,
      "total_charges": 1919.76
    }
  }'
```

Response:
```json
{
  "predictions": [1],
  "model_name": "customer_churn_predictor",
  "model_version": "3",
  "count": 1,
  "timestamp": "2025-11-15T10:35:00Z",
  "latency_ms": 12.5
}
```

**Batch Prediction**
```bash
curl -X POST "http://localhost:8004/serving/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "customer_churn_predictor",
    "model_stage": "Production",
    "instances": [
      {"age": 35, "tenure_months": 24, ...},
      {"age": 42, "tenure_months": 48, ...}
    ]
  }'
```

**Probability Prediction**
```bash
curl -X POST "http://localhost:8004/serving/predict_proba" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "customer_churn_predictor",
    "features": {...}
  }'
```

**Get Loaded Models**
```bash
curl "http://localhost:8004/serving/models"
```

## Configuration

### Environment Variables

```bash
# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_S3_ENDPOINT_URL=http://minio:9000  # For artifact storage
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Application
DATAFORGE_ENV=production
LOG_LEVEL=INFO
API_PORT=8004

# Model serving
MODEL_CACHE_SIZE=10
PREDICTION_TIMEOUT=30
```

## Use Cases

### 1. Experiment Tracking

Track multiple model variations:

```python
experiments = [
    ("random_forest", RandomForestClassifier, {...}),
    ("xgboost", XGBClassifier, {...}),
    ("lightgbm", LGBMClassifier, {...}),
]

for name, model_class, params in experiments:
    with tracker.start_run(run_name=name):
        model = model_class(**params)
        result = trainer.train(X, y, model)

        tracker.log_params(params)
        tracker.log_metrics({
            "f1_score": result.test_score,
            "cv_mean": result.cv_mean
        })
        tracker.log_model(result.model, "model")

# Compare all runs
best = tracker.get_best_run("f1_score")
```

### 2. A/B Testing Models

Deploy multiple models:

```python
# Deploy challenger model
registry.register_model(
    model_uri="runs:/challenger_run/model",
    name="churn_predictor_challenger"
)
registry.promote_to_production("churn_predictor_challenger", "1")

# Compare with champion
champion_pred = server.predict("churn_predictor", ...)
challenger_pred = server.predict("churn_predictor_challenger", ...)
```

### 3. Model Rollback

Rollback to previous version:

```python
# If production model fails
current_prod = registry.get_production_model("churn_predictor")

# Rollback to previous version
registry.rollback_production("churn_predictor", to_version="2")
```

### 4. Automated Retraining

Schedule periodic retraining:

```python
# In Airflow DAG
def retrain_model():
    # Load latest data
    X, y = load_latest_data()

    # Train
    result = trainer.train_with_tuning(X, y, XGBClassifier, param_space)

    # Log to MLflow
    tracker.log_model(result.model, "model")

    # Register if better than current
    if result.test_score > current_best:
        version = registry.register_model(...)
        registry.promote_to_production(...)
```

## Integration with Other Accelerators

### With Pipeline Automation (Accelerator 1)

Automate model training in DAGs:

```python
# Airflow DAG
train_task = PythonOperator(
    task_id="train_model",
    python_callable=train_and_register_model
)
```

### With Data Catalog (Accelerator 4)

Track model-dataset lineage:

```python
# Register model with dataset metadata
registry.register_model(
    ...,
    tags={
        "dataset_id": "analytics.customer_features_v2",
        "feature_version": "2.1"
    }
)
```

## Deployment

### Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### Docker

```bash
docker build -t model-factory:latest .
docker run -p 8004:8004 \
  -e MLFLOW_TRACKING_URI=http://mlflow:5000 \
  model-factory:latest
```

## Monitoring

Access Prometheus metrics at `/metrics`:

- `predictions_total`: Total predictions made
- `models_registered_total`: Total models registered
- `production_promotions_total`: Models promoted to production
- `prediction_latency_ms`: Prediction latency

## Testing

```bash
pytest tests/ -v
```

## Limitations

1. **In-Memory Cache**: Model server uses in-memory cache. For distributed serving, use Redis or dedicated model serving platform (TensorFlow Serving, Seldon).
2. **Local MLflow**: Current setup uses local MLflow. For production, deploy MLflow server with database backend.
3. **No GPU Support**: Current implementation doesn't include GPU optimization. Add CUDA support for deep learning models.

## Roadmap

- [ ] GPU support for deep learning models
- [ ] Model monitoring and drift detection
- [ ] Automated model validation
- [ ] Shadow deployments
- [ ] Canary releases
- [ ] Model explainability (SHAP, LIME)
- [ ] Feature store integration
- [ ] Online learning support
- [ ] Model compression and optimization
- [ ] Multi-model ensembles

## Troubleshooting

### Issue: MLflow connection failed

Start MLflow server:
```bash
mlflow server --backend-store-uri sqlite:///mlflow.db \
              --default-artifact-root ./mlruns \
              --host 0.0.0.0 --port 5000
```

### Issue: Model not loading

Check if model is registered and in correct stage:
```python
registry.list_models()
registry.get_production_model("model_name")
```

### Issue: Slow predictions

1. Load model into cache before first prediction
2. Use batch predictions for multiple instances
3. Consider model compression

## License

Part of DataForge AI Platform - MIT License
