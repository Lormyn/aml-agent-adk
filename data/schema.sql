-- Create Users Table
CREATE TABLE `aml_dataset.users` (
    user_id STRING,
    name STRING,
    occupation STRING,
    email STRING,
    phone STRING,
    address STRING,
    annual_income INT64,
    risk_score FLOAT64,
    joined_date DATE
);

-- Create Transactions Table
CREATE TABLE `aml_dataset.transactions` (
    txn_id STRING,
    sender_id STRING,
    receiver_id STRING,
    amount FLOAT64,
    currency STRING,
    timestamp TIMESTAMP,
    txn_type STRING
);

-- Create Alerts Table
CREATE TABLE `aml_dataset.alerts` (
    alert_id STRING,
    user_id STRING,
    trigger_reason STRING,
    status STRING,
    created_at TIMESTAMP,
    severity STRING
);
