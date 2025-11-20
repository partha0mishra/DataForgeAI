from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.providers.apache.kafka.sensors.kafka import AwaitMessageSensor
from airflow.models import Variable
import json
from confluent_kafka import Consumer, KafkaError
import snowflake.connector

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['alerts@company.com'],
    'email_on_failure': True,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}


def consume_cdc_events(**context):
    """Consume CDC events from Kafka and stage in S3."""
    import boto3
    from io import StringIO

    # Kafka configuration
    kafka_config = {
        'bootstrap.servers': 'kafka-1:9092,kafka-2:9092,kafka-3:9092',
        'group.id': 'snowflake-sink',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
    }

    consumer = Consumer(kafka_config)
    topics = ['oracle.cdc.SALES.ORDERS', 'oracle.cdc.SALES.ORDER_ITEMS', 'oracle.cdc.INVENTORY.PRODUCTS']
    consumer.subscribe(topics)

    s3_client = boto3.client('s3')
    batch_size = 1000
    messages = []

    try:
        for _ in range(batch_size):
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    break
                else:
                    raise Exception(msg.error())

            # Parse CDC event
            event = json.loads(msg.value().decode('utf-8'))
            messages.append(event)

        # Write to S3 in Snowflake-compatible format
        if messages:
            execution_date = context['ds']
            for topic in topics:
                topic_messages = [m for m in messages if m['source']['table'] in topic]
                if topic_messages:
                    table_name = topic_messages[0]['source']['table']
                    s3_key = f"cdc-staging/{table_name}/{execution_date}/data.json"

                    json_buffer = StringIO()
                    for msg in topic_messages:
                        json_buffer.write(json.dumps(msg) + '\n')

                    s3_client.put_object(
                        Bucket='your-bucket',
                        Key=s3_key,
                        Body=json_buffer.getvalue()
                    )

        consumer.commit()
    finally:
        consumer.close()

    return len(messages)


def apply_cdc_to_snowflake(**context):
    """Apply CDC changes to Snowflake using MERGE statements."""

    conn = snowflake.connector.connect(
        user=Variable.get('snowflake_user'),
        password=Variable.get('snowflake_password'),
        account='xy12345.us-east-1',
        warehouse='COMPUTE_WH',
        database='CDC_ANALYTICS',
        schema='BRONZE'
    )

    cursor = conn.cursor()

    try:
        # Process ORDERS table
        merge_sql = """
        MERGE INTO CDC_ANALYTICS.BRONZE.ORDERS AS target
        USING (
            SELECT
                after:ORDER_ID::NUMBER AS ORDER_ID,
                after:CUSTOMER_ID::NUMBER AS CUSTOMER_ID,
                after:ORDER_DATE::TIMESTAMP AS ORDER_DATE,
                after:TOTAL_AMOUNT::NUMBER(10,2) AS TOTAL_AMOUNT,
                after:STATUS::VARCHAR AS STATUS,
                source:scn::VARCHAR AS SCN,
                source:ts_ms::NUMBER AS CHANGE_TS,
                op::VARCHAR AS OPERATION
            FROM @CDC_ANALYTICS.EXTERNAL_STAGES.S3_CDC_STAGE/ORDERS/{{ ds }}/
            (FILE_FORMAT => 'JSON_FORMAT')
        ) AS source
        ON target.ORDER_ID = source.ORDER_ID
        WHEN MATCHED AND source.OPERATION = 'u' THEN
            UPDATE SET
                CUSTOMER_ID = source.CUSTOMER_ID,
                ORDER_DATE = source.ORDER_DATE,
                TOTAL_AMOUNT = source.TOTAL_AMOUNT,
                STATUS = source.STATUS,
                UPDATED_SCN = source.SCN,
                UPDATED_AT = TO_TIMESTAMP(source.CHANGE_TS / 1000)
        WHEN MATCHED AND source.OPERATION = 'd' THEN
            UPDATE SET
                IS_DELETED = TRUE,
                DELETED_SCN = source.SCN,
                DELETED_AT = TO_TIMESTAMP(source.CHANGE_TS / 1000)
        WHEN NOT MATCHED AND source.OPERATION = 'c' THEN
            INSERT (ORDER_ID, CUSTOMER_ID, ORDER_DATE, TOTAL_AMOUNT, STATUS, CREATED_SCN, CREATED_AT)
            VALUES (source.ORDER_ID, source.CUSTOMER_ID, source.ORDER_DATE,
                    source.TOTAL_AMOUNT, source.STATUS, source.SCN,
                    TO_TIMESTAMP(source.CHANGE_TS / 1000));
        """

        cursor.execute(merge_sql)

        # Process ORDER_ITEMS table
        merge_sql = """
        MERGE INTO CDC_ANALYTICS.BRONZE.ORDER_ITEMS AS target
        USING (
            SELECT
                after:ORDER_ITEM_ID::NUMBER AS ORDER_ITEM_ID,
                after:ORDER_ID::NUMBER AS ORDER_ID,
                after:PRODUCT_ID::NUMBER AS PRODUCT_ID,
                after:QUANTITY::NUMBER AS QUANTITY,
                after:UNIT_PRICE::NUMBER(10,2) AS UNIT_PRICE,
                after:SUBTOTAL::NUMBER(10,2) AS SUBTOTAL,
                source:scn::VARCHAR AS SCN,
                source:ts_ms::NUMBER AS CHANGE_TS,
                op::VARCHAR AS OPERATION
            FROM @CDC_ANALYTICS.EXTERNAL_STAGES.S3_CDC_STAGE/ORDER_ITEMS/{{ ds }}/
            (FILE_FORMAT => 'JSON_FORMAT')
        ) AS source
        ON target.ORDER_ITEM_ID = source.ORDER_ITEM_ID
        WHEN MATCHED AND source.OPERATION = 'u' THEN
            UPDATE SET
                QUANTITY = source.QUANTITY,
                UNIT_PRICE = source.UNIT_PRICE,
                SUBTOTAL = source.SUBTOTAL,
                UPDATED_SCN = source.SCN,
                UPDATED_AT = TO_TIMESTAMP(source.CHANGE_TS / 1000)
        WHEN MATCHED AND source.OPERATION = 'd' THEN
            UPDATE SET
                IS_DELETED = TRUE,
                DELETED_SCN = source.SCN,
                DELETED_AT = TO_TIMESTAMP(source.CHANGE_TS / 1000)
        WHEN NOT MATCHED AND source.OPERATION = 'c' THEN
            INSERT (ORDER_ITEM_ID, ORDER_ID, PRODUCT_ID, QUANTITY, UNIT_PRICE, SUBTOTAL, CREATED_SCN, CREATED_AT)
            VALUES (source.ORDER_ITEM_ID, source.ORDER_ID, source.PRODUCT_ID,
                    source.QUANTITY, source.UNIT_PRICE, source.SUBTOTAL, source.SCN,
                    TO_TIMESTAMP(source.CHANGE_TS / 1000));
        """

        cursor.execute(merge_sql)

        conn.commit()
    finally:
        cursor.close()
        conn.close()


with DAG(
    dag_id='oracle_cdc_to_snowflake',
    default_args=default_args,
    schedule_interval='*/5 * * * *',  # Every 5 minutes
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['cdc', 'oracle', 'snowflake', 'realtime'],
) as dag:

    consume_kafka = PythonOperator(
        task_id='consume_cdc_events',
        python_callable=consume_cdc_events,
        provide_context=True,
    )

    apply_changes = PythonOperator(
        task_id='apply_cdc_to_snowflake',
        python_callable=apply_cdc_to_snowflake,
        provide_context=True,
    )

    validate_data = SnowflakeOperator(
        task_id='validate_data_quality',
        snowflake_conn_id='snowflake_default',
        sql="""
        SELECT
            COUNT(*) AS total_records,
            SUM(CASE WHEN IS_DELETED THEN 1 ELSE 0 END) AS deleted_records,
            MAX(UPDATED_AT) AS last_update
        FROM CDC_ANALYTICS.BRONZE.ORDERS;
        """,
    )

    consume_kafka >> apply_changes >> validate_data
