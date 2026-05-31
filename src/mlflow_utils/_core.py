import functools
import json
import os
import tempfile
from typing import Any, Callable

import mlflow
import pandas as pd

from src.config import DEFAULT_MLFLOW_EXPERIMENT, DEFAULT_MLFLOW_TRACKING_URI
from src.logger import get_logger


logger = get_logger(__name__)


def init_mlflow(experiment_name: str | None = None) -> str:
    """
    Initialize MLflow tracking URI and set the current experiment.
    If the experiment does not exist, it will be created.

    Args:
        experiment_name: Name of the experiment to set. Defaults to config's default.

    Returns:
        The active experiment ID.
    """
    tracking_uri = DEFAULT_MLFLOW_TRACKING_URI
    mlflow.set_tracking_uri(tracking_uri)
    logger.info(f"MLflow tracking URI set to: {tracking_uri}")

    exp_name = experiment_name or DEFAULT_MLFLOW_EXPERIMENT
    
    # Check if experiment exists, otherwise create it
    experiment = mlflow.get_experiment_by_name(exp_name)
    if experiment is None:
        logger.info(f"Experiment '{exp_name}' does not exist. Creating it.")
        try:
            experiment_id = mlflow.create_experiment(exp_name)
        except Exception as e:
            # Fallback in case of race condition or file lock
            logger.warning(f"Failed to create experiment: {e}. Trying to fetch it.")
            experiment = mlflow.get_experiment_by_name(exp_name)
            if experiment is not None:
                experiment_id = experiment.experiment_id
            else:
                raise
    else:
        experiment_id = experiment.experiment_id

    mlflow.set_experiment(experiment_name=exp_name)
    logger.info(f"Active MLflow experiment set to '{exp_name}' (ID: {experiment_id})")
    return experiment_id


def track_run(experiment_name: str | None = None, run_name: str | None = None) -> Callable:
    """
    Decorator to wrap a function with an MLflow run.
    Automatically starts and ends the run, setting the experiment.
    If an exception is raised inside the function, the decorator logs
    the error to MLflow parameters, sets the run status to FAILED, and re-raises.

    Args:
        experiment_name: Name of the experiment. Defaults to config's default.
        run_name: Name of the run. Defaults to the decorated function's name.

    Returns:
        Decorated function.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            init_mlflow(experiment_name)
            
            active_run_name = run_name or func.__name__
            logger.info(f"Starting MLflow run: '{active_run_name}'")

            # Check if there is already an active run to handle nested runs cleanly
            if mlflow.active_run() is not None:
                logger.info("Using existing active MLflow run.")
                return func(*args, **kwargs)

            with mlflow.start_run(run_name=active_run_name) as run:
                try:
                    result = func(*args, **kwargs)
                    logger.info(f"Successfully completed MLflow run: '{active_run_name}'")
                    return result
                except Exception as e:
                    logger.error(f"Error during execution in MLflow run '{active_run_name}': {e}")
                    mlflow.log_param("execution_failed", True)
                    mlflow.log_param("error_type", type(e).__name__)
                    mlflow.log_param("error_message", str(e))
                    # Mark status as failed via system exit/exception behavior
                    raise e
        return wrapper
    return decorator


def log_dataframe_summary(df: pd.DataFrame, artifact_name: str = "dataset_summary.json") -> None:
    """
    Generates summary statistics of a pandas DataFrame and logs it as a JSON artifact
    to the active MLflow run.

    Args:
        df: The pandas DataFrame to summarize.
        artifact_name: Filename of the logged artifact. Defaults to "dataset_summary.json".
    """
    if mlflow.active_run() is None:
        logger.warning("No active MLflow run. Skipping logging dataframe summary.")
        return

    logger.info(f"Generating and logging DataFrame summary for artifact '{artifact_name}'")
    
    # Calculate dataset statistics
    summary = {
        "shape": list(df.shape),
        "columns": list(df.columns),
        "index_name": df.index.name,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "null_counts": df.isnull().sum().to_dict(),
        "describe": df.describe(include="all").to_dict() if not df.empty else {},
    }

    # Custom handling for Timestamp keys in describe dict (since json doesn't serialize Timestamp)
    def clean_dict(d: Any) -> Any:
        if isinstance(d, dict):
            return {str(k): clean_dict(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [clean_dict(x) for x in d]
        elif isinstance(d, (pd.Timestamp, date := pd.Timestamp)):
            return d.isoformat()
        elif pd.isna(d):
            return None
        return d

    clean_summary = clean_dict(summary)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = os.path.join(temp_dir, artifact_name)
        with open(temp_file_path, "w") as f:
            json.dump(clean_summary, f, indent=4)
        
        mlflow.log_artifact(temp_file_path)
    
    logger.info(f"DataFrame summary successfully logged to MLflow as '{artifact_name}'")
