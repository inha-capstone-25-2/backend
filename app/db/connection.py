import os
import mysql.connector
import boto3

# MySQL 연결 설정
def get_mysql_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# DynamoDB 연결 설정
def get_dynamodb_resource():
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    return dynamodb