"""dbt transformation DAG."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

from dataforge_common.logging import get_logger

logger = get_logger(__name__)

default_args = {
    "owner": "dataforge",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# dbt project path
DBT_PROJECT_PATH = "/opt/airflow/dags/dbt"

with DAG(
    dag_id="dbt_transformation",
    default_args=default_args,
    description="Run dbt transformations",
    schedule="@daily",
    catchup=False,
    tags=["dbt", "transformation"],
) as dag:

    # Task 1: dbt deps (install dependencies)
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {DBT_PROJECT_PATH} && dbt deps",
    )

    # Task 2: dbt run staging models
    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=f"cd {DBT_PROJECT_PATH} && dbt run --models staging.*",
    )

    # Task 3: dbt run intermediate models
    dbt_run_intermediate = BashOperator(
        task_id="dbt_run_intermediate",
        bash_command=f"cd {DBT_PROJECT_PATH} && dbt run --models intermediate.*",
    )

    # Task 4: dbt run marts
    dbt_run_marts = BashOperator(
        task_id="dbt_run_marts",
        bash_command=f"cd {DBT_PROJECT_PATH} && dbt run --models marts.*",
    )

    # Task 5: dbt test
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT_PATH} && dbt test",
    )

    # Task 6: dbt docs generate
    dbt_docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"cd {DBT_PROJECT_PATH} && dbt docs generate",
    )

    # Define dependencies
    dbt_deps >> dbt_run_staging >> dbt_run_intermediate >> dbt_run_marts >> dbt_test >> dbt_docs
