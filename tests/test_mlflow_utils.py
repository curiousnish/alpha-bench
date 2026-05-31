import os
import shutil
import tempfile
import pytest
import pandas as pd
import mlflow

from src.mlflow_utils import init_mlflow, track_run, log_dataframe_summary


@pytest.fixture(scope="function", autouse=True)
def setup_temp_mlflow(monkeypatch):
    """
    Fixture to isolate MLflow tracking during tests.
    Sets a temporary tracking directory and resets it after each test.
    """
    temp_dir = tempfile.mkdtemp()
    temp_uri = f"file://{temp_dir}"
    
    # Monkeypatch the default tracking URI to isolate tests from real mlruns
    from src.mlflow_utils import _core
    monkeypatch.setattr(_core, "DEFAULT_MLFLOW_TRACKING_URI", temp_uri)
    
    # Store old URI and set to temp URI
    old_uri = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(temp_uri)
    
    yield temp_uri
    
    # Cleanup temp directory and restore original URI
    if mlflow.active_run() is not None:
        mlflow.end_run()
    
    mlflow.set_tracking_uri(old_uri)
    
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass



def test_init_mlflow():
    """
    Test that init_mlflow correctly initializes an experiment and sets the active experiment.
    """
    exp_name = "test_experiment_xyz"
    
    exp_id = init_mlflow(experiment_name=exp_name)
    assert exp_id is not None
    assert isinstance(exp_id, str)
    
    # Verify active experiment is set
    active_exp = mlflow.get_experiment_by_name(exp_name)
    assert active_exp is not None
    assert active_exp.experiment_id == exp_id
    assert active_exp.name == exp_name


def test_track_run_success():
    """
    Test that @track_run decorator manages the run lifecycle and logs successful runs.
    """
    exp_name = "test_decorator_success_exp"
    run_name = "test_run_success"
    
    @track_run(experiment_name=exp_name, run_name=run_name)
    def dummy_func(x, y):
        mlflow.log_param("input_x", x)
        return x + y

    res = dummy_func(5, 10)
    assert res == 15
    
    # The run should have finished, so no active run should exist now
    assert mlflow.active_run() is None
    
    # Retrieve the run to verify its properties
    exp = mlflow.get_experiment_by_name(exp_name)
    runs = mlflow.search_runs(experiment_ids=[exp.experiment_id])
    
    assert len(runs) == 1
    run_data = runs.iloc[0]
    assert run_data["tags.mlflow.runName"] == run_name
    assert run_data["params.input_x"] == "5"
    assert run_data["status"] == "FINISHED"


def test_track_run_failure():
    """
    Test that @track_run decorator logs failure parameters when the decorated function raises an exception.
    """
    exp_name = "test_decorator_failure_exp"
    run_name = "test_run_failure"
    
    @track_run(experiment_name=exp_name, run_name=run_name)
    def failing_func():
        raise ValueError("Something went wrong in model training.")

    with pytest.raises(ValueError) as excinfo:
        failing_func()
        
    assert "Something went wrong" in str(excinfo.value)
    
    # No active run should remain open
    assert mlflow.active_run() is None
    
    # Retrieve the run to verify error logging
    exp = mlflow.get_experiment_by_name(exp_name)
    runs = mlflow.search_runs(experiment_ids=[exp.experiment_id])
    
    assert len(runs) == 1
    run_data = runs.iloc[0]
    assert run_data["params.execution_failed"] == "True"
    assert run_data["params.error_type"] == "ValueError"
    assert "Something went wrong" in run_data["params.error_message"]
    assert run_data["status"] == "FAILED"


def test_log_dataframe_summary():
    """
    Test that log_dataframe_summary successfully creates and uploads a JSON profile artifact.
    """
    exp_name = "test_summary_exp"
    init_mlflow(exp_name)
    
    # Create a dummy dataframe
    df = pd.DataFrame({
        "Open": [100.0, 101.0, 102.0],
        "Close": [101.0, 102.0, 103.0],
        "Volume": [1000, 1100, 1200]
    })
    df.index.name = "Date"
    
    with mlflow.start_run() as run:
        log_dataframe_summary(df, artifact_name="test_summary.json")
        run_id = run.info.run_id
        
    # Verify that the artifact was logged
    client = mlflow.tracking.MlflowClient()
    artifacts = client.list_artifacts(run_id)
    
    artifact_paths = [art.path for art in artifacts]
    assert "test_summary.json" in artifact_paths
