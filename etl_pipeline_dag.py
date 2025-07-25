"""
ETL Pipeline Airflow DAG
Orchestrates the complete ETL workflow with dependencies and monitoring
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
from airflow.providers.postgres.operators.postgres import PostgresOperator

# Default arguments for the DAG
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

# Create DAG
dag = DAG(
    'etl_pipeline',
    default_args=default_args,
    description='Complete ETL Pipeline for Customer Data',
    schedule_interval='@daily',
    max_active_runs=1,
    tags=['etl', 'data-pipeline', 'customer-data'],
)

def extract_customer_data(**context):
    """Extract customer data from CSV"""
    from src.extract.data_extractors import CSVExtractor

    extractor = CSVExtractor('data/raw/customers.csv')
    df = extractor.extract()

    # Store extracted data
    df.to_parquet(f"data/staging/customers_{context['ds']}.parquet")

    return len(df)

def extract_transaction_data(**context):
    """Extract transaction data from database"""
    from src.extract.data_extractors import DatabaseExtractor

    extractor = DatabaseExtractor('postgresql://etl_user:etl_pass@postgres/etl_db')
    df = extractor.extract()

    # Store extracted data
    df.to_parquet(f"data/staging/transactions_{context['ds']}.parquet")

    return len(df)

def transform_data(**context):
    """Transform and clean data"""
    import pandas as pd
    from src.transform.data_cleaners import DataCleaner
    from src.transform.data_validators import DataValidator

    # Load staged data
    customers_df = pd.read_parquet(f"data/staging/customers_{context['ds']}.parquet")
    transactions_df = pd.read_parquet(f"data/staging/transactions_{context['ds']}.parquet")

    # Apply transformations
    cleaner = DataCleaner()
    validator = DataValidator()

    customers_clean = cleaner.clean_customer_data(customers_df)
    transactions_clean = cleaner.clean_transaction_data(transactions_df)

    customers_valid = validator.validate_customers(customers_clean)
    transactions_valid = validator.validate_transactions(transactions_clean)

    # Join and aggregate
    final_df = customers_valid.merge(transactions_valid, on='customer_id')
    agg_df = final_df.groupby(['customer_id']).agg({
        'amount': ['sum', 'mean', 'count']
    })

    # Save transformed data
    agg_df.to_parquet(f"data/processed/customer_summary_{context['ds']}.parquet")

    return len(agg_df)

def load_to_warehouse(**context):
    """Load data to data warehouse"""
    import pandas as pd
    from src.load.data_loaders import DatabaseLoader

    # Load processed data
    df = pd.read_parquet(f"data/processed/customer_summary_{context['ds']}.parquet")

    # Load to warehouse
    loader = DatabaseLoader('postgresql://etl_user:etl_pass@postgres/warehouse_db')
    loader.load(df, table_name='customer_summary')

    return len(df)

def data_quality_check(**context):
    """Perform data quality checks"""
    import pandas as pd

    df = pd.read_parquet(f"data/processed/customer_summary_{context['ds']}.parquet")

    # Basic quality checks
    null_percentage = df.isnull().sum().sum() / (len(df) * len(df.columns))
    duplicate_count = df.duplicated().sum()

    # Alert if quality thresholds exceeded
    if null_percentage > 0.05:
        raise ValueError(f"Data quality issue: {null_percentage:.2%} null values")

    if duplicate_count > 0:
        raise ValueError(f"Data quality issue: {duplicate_count} duplicate records")

    return {"null_percentage": null_percentage, "duplicate_count": duplicate_count}

# Define tasks
check_source_data = FileSensor(
    task_id='check_source_data',
    filepath='data/raw/customers.csv',
    fs_conn_id='fs_default',
    poke_interval=30,
    timeout=600,
    dag=dag,
)

extract_customers = PythonOperator(
    task_id='extract_customers',
    python_callable=extract_customer_data,
    dag=dag,
)

extract_transactions = PythonOperator(
    task_id='extract_transactions', 
    python_callable=extract_transaction_data,
    dag=dag,
)

transform = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    dag=dag,
)

quality_check = PythonOperator(
    task_id='data_quality_check',
    python_callable=data_quality_check,
    dag=dag,
)

load_warehouse = PythonOperator(
    task_id='load_to_warehouse',
    python_callable=load_to_warehouse,
    dag=dag,
)

cleanup = BashOperator(
    task_id='cleanup_staging',
    bash_command='rm -f data/staging/*{{ ds }}*',
    dag=dag,
)

# Set task dependencies
check_source_data >> [extract_customers, extract_transactions]
[extract_customers, extract_transactions] >> transform
transform >> quality_check >> load_warehouse >> cleanup
