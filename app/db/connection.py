import os
import mysql.connector
import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

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

# MongoDB 연결 설정
def get_mongo_collection():
    host = os.getenv("MONGO_HOST")
    port = int(os.getenv("MONGO_PORT", "27017"))
    user = os.getenv("MONGO_USER")
    password = os.getenv("MONGO_PASSWORD")
    auth_source = os.getenv("MONGO_AUTH_SOURCE", "admin")
    db_name = os.getenv("MONGO_DB", "arxiv")
    collection_name = os.getenv("MONGO_COLLECTION", "arxiv_papers")

    if not host:
        logger.error("MONGO_HOST is not set.")
        return None, None

    if user and password:
        mongo_uri = f"mongodb://{user}:{password}@{host}:{port}/?authSource={auth_source}"
    else:
        mongo_uri = f"mongodb://{host}:{port}/"

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[db_name]
        coll = db[collection_name]
        coll.create_index("id", unique=True)
        return client, coll
    except PyMongoError as e:
        logger.error(f"Error: {e}")
        return None, None
