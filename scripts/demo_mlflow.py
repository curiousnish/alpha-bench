"""
scripts/demo_mlflow.py — Comprehensive end-to-end demo of MLflow experiment tracking.

Fetches stock market data using Alpha-Bench fetchers, engineers features, trains
a model (RandomForestClassifier) to predict price direction, performs a hyperparameter
grid search with nested runs, logs metrics, parameters, diagnostic plots, and models,
and retrieves the best model from the registry/run history.

Usage:
    uv run python scripts/demo_mlflow.py
"""

import os
import tempfile
import time
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.metrics import ConfusionMatrixDisplay

import mlflow
from src.config import DEFAULT_MLFLOW_EXPERIMENT
from src.data_fetchers import fetch_jugaad_ohlcv, fetch_yfinance_ohlcv
from src.logger import get_logger, setup_logging
from src.mlflow_utils import init_mlflow, log_dataframe_summary, track_run


logger = get_logger(__name__)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer predictive features for stock price movement.
    """
    df = df.copy()

    # Technical indicators
    df["Daily_Return"] = df["Close"].pct_change()
    df["SMA_5"] = df["Close"].rolling(window=5).mean()
    df["SMA_10"] = df["Close"].rolling(window=10).mean()
    df["SMA_Ratio"] = df["SMA_5"] / df["SMA_10"]
    df["Volatility_5"] = df["Daily_Return"].rolling(window=5).std()

    # Lagged features
    df["Lag_Close_1"] = df["Close"].shift(1)
    df["Lag_Close_2"] = df["Close"].shift(2)
    df["Lag_Return_1"] = df["Daily_Return"].shift(1)

    # Target variable: 1 if next day's Close > today's Close, else 0
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

    # Drop NaNs created by rolling and lagging
    df = df.dropna()
    return df


@track_run(run_name="Stock_Direction_Classifier_Parent")
def run_modeling_pipeline(ticker: str, source: str = "yfinance") -> None:
    """
    Runs the entire pipeline: fetching data, engineering features,
    running a nested grid search, and logging everything to MLflow.
    """
    logger.info(f"Starting modeling pipeline for '{ticker}' using '{source}'")

    # 1. Fetch historical data (e.g., past 90 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    if source.lower() == "jugaad":
        df = fetch_jugaad_ohlcv(ticker, start_date=start_date, end_date=end_date)
    else:
        df = fetch_yfinance_ohlcv(ticker, start_date=start_date, end_date=end_date)

    if df.empty or len(df) < 20:
        logger.error("Insufficient data fetched for modeling. Exiting pipeline.")
        return

    # Log parent-level metadata
    mlflow.log_param("ticker", ticker)
    mlflow.log_param("data_source", source)
    mlflow.log_param("data_start_date", start_date.strftime("%Y-%m-%d"))
    mlflow.log_param("data_end_date", end_date.strftime("%Y-%m-%d"))
    mlflow.log_param("total_raw_records", len(df))

    # Log dataset summary as an artifact
    log_dataframe_summary(df, artifact_name="raw_dataset_summary.json")

    # 2. Feature Engineering
    df_features = engineer_features(df)
    logger.info(f"Features engineered. Dataset shape after engineering: {df_features.shape}")
    
    # Define features and target
    feature_cols = [
        "Daily_Return", "SMA_Ratio", "Volatility_5",
        "Lag_Close_1", "Lag_Close_2", "Lag_Return_1"
    ]
    X = df_features[feature_cols]
    y = df_features["Target"]

    # 3. Time-series Train/Test Split (Avoid lookahead bias)
    split_idx = int(len(df_features) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    mlflow.log_param("features_list", feature_cols)
    mlflow.log_param("train_set_size", len(X_train))
    mlflow.log_param("test_set_size", len(X_test))

    # 4. Hyperparameter Grid Search using Nested MLflow Runs
    hyperparam_grid = [
        {"n_estimators": 25, "max_depth": 3},
        {"n_estimators": 50, "max_depth": 5},
        {"n_estimators": 100, "max_depth": 7},
    ]

    best_accuracy = -1.0
    best_run_id = None

    for i, params in enumerate(hyperparam_grid):
        trial_name = f"Trial_{i + 1}_n{params['n_estimators']}_d{params['max_depth']}"
        logger.info(f"Running nested trial: '{trial_name}' with parameters {params}")

        # Start a nested (child) run
        with mlflow.start_run(run_name=trial_name, nested=True) as child_run:
            # Train model
            model = RandomForestClassifier(
                n_estimators=params["n_estimators"],
                max_depth=params["max_depth"],
                random_state=42
            )
            model.fit(X_train, y_train)

            # Predict and evaluate
            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            prec = precision_score(y_test, y_pred, zero_division=0)
            rec = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)

            logger.info(f"Trial Results - Accuracy: {acc:.4f}, F1: {f1:.4f}")

            # Log parameters
            mlflow.log_params(params)

            # Log metrics
            mlflow.log_metric("test_accuracy", acc)
            mlflow.log_metric("test_precision", prec)
            mlflow.log_metric("test_recall", rec)
            mlflow.log_metric("test_f1", f1)

            # Log the model itself
            mlflow.sklearn.log_model(model, artifact_path="model")

            # Create and log diagnostic plots
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. Confusion Matrix
                fig, ax = plt.subplots(figsize=(6, 5))
                ConfusionMatrixDisplay.from_predictions(y_test, y_pred, ax=ax, cmap="Blues")
                ax.set_title(f"Confusion Matrix - {trial_name}")
                plot_path = os.path.join(temp_dir, "confusion_matrix.png")
                plt.savefig(plot_path, bbox_inches="tight")
                plt.close(fig)
                mlflow.log_artifact(plot_path)

                # 2. Feature Importance
                fig, ax = plt.subplots(figsize=(8, 5))
                importances = model.feature_importances_
                indices = np.argsort(importances)
                ax.barh(range(len(indices)), importances[indices], color="steelblue", align="center")
                ax.set_yticks(range(len(indices)))
                ax.set_yticklabels([feature_cols[idx] for idx in indices])
                ax.set_xlabel("Relative Importance")
                ax.set_title(f"Feature Importance - {trial_name}")
                importance_path = os.path.join(temp_dir, "feature_importance.png")
                plt.savefig(importance_path, bbox_inches="tight")
                plt.close(fig)
                mlflow.log_artifact(importance_path)

            if acc > best_accuracy:
                best_accuracy = acc
                best_run_id = child_run.info.run_id

    # Log best trial performance to parent
    if best_run_id:
        mlflow.log_param("best_child_run_id", best_run_id)
        mlflow.log_metric("best_test_accuracy", best_accuracy)
        logger.info(f"Pipeline completed. Best nested trial achieved accuracy: {best_accuracy:.4f}")


def query_and_load_best_model() -> None:
    """
    Demonstrates how to query MLflow to find the best model
    and print its metadata.
    """
    logger.info("=========================================")
    logger.info("Querying MLflow for the Best Performing Model")
    logger.info("=========================================")

    # Initialize mlflow to ensure tracking URI is set
    init_mlflow()

    # Search for runs in the active experiment
    experiment = mlflow.get_experiment_by_name(DEFAULT_MLFLOW_EXPERIMENT)
    if not experiment:
        logger.warning("No experiment found to query.")
        return

    # Retrieve all runs sorted by test_accuracy descending
    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="metrics.test_accuracy > 0",
        order_by=["metrics.test_accuracy DESC"]
    )

    if runs.empty:
        logger.info("No completed model runs found with 'test_accuracy' metrics.")
        return

    best_run = runs.iloc[0]
    run_id = best_run["run_id"]
    accuracy = best_run["metrics.test_accuracy"]
    run_name = best_run["tags.mlflow.runName"]

    print(f"🥇 Best Run Name: {run_name}")
    print(f"🆔 Run ID: {run_id}")
    print(f"🎯 Test Accuracy: {accuracy:.4f}")
    print(f"📦 Model Artifact URI: {best_run['artifact_uri']}/model")
    print()


def main():
    setup_logging(default_level="INFO", console_output=True)

    logger.info("=========================================")
    logger.info("Starting Alpha-Bench MLflow Modeling Demo")
    logger.info("=========================================")

    # 1. Run pipeline using yfinance data (TCS)
    try:
        run_modeling_pipeline(ticker="TCS", source="yfinance")
    except Exception as e:
        logger.error(f"Error running yfinance pipeline: {e}", exc_info=True)

    time.sleep(1.0)

    # 2. Run pipeline using jugaad-data (RELIANCE)
    try:
        run_modeling_pipeline(ticker="RELIANCE", source="jugaad")
    except Exception as e:
        logger.error(f"Error running jugaad-data pipeline: {e}", exc_info=True)

    time.sleep(1.0)

    # 3. Query and load the best model
    query_and_load_best_model()

    logger.info("MLflow modeling demo pipeline execution completed.")


if __name__ == "__main__":
    main()
