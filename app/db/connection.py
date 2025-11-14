import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from app.core.settings import settings

logger = logging.getLogger(__name__)

# MongoDB 연결 설정
def get_mongo_collection():
    host = settings.mongo_host
    port = settings.mongo_port
    user = settings.mongo_user
    password = settings.mongo_password
    auth_source = settings.mongo_auth_source
    db_name = settings.mongo_db
    collection_name = settings.mongo_collection

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
        return client, coll
    except PyMongoError as e:
        logger.error(f"Error: {e}")
        return None, None

def get_mongo_collection_for_search():
    """
    논문 검색 전용 Mongo 커넥션.
    - PROD_MONGO_* 환경변수가 있으면 그것을 우선 사용(로컬에서도 prod 접속 가능)
    - 없으면 기본 MONGO_*로 폴백
    """
    host = settings.prod_mongo_host or settings.mongo_host
    port = settings.prod_mongo_port or settings.mongo_port
    user = settings.prod_mongo_user if settings.prod_mongo_user is not None else settings.mongo_user
    password = settings.prod_mongo_password if settings.prod_mongo_password is not None else settings.mongo_password
    auth_source = settings.prod_mongo_auth_source or settings.mongo_auth_source
    db_name = settings.prod_mongo_db or settings.mongo_db
    collection_name = settings.prod_mongo_collection or settings.mongo_collection

    if not host:
        logger.error("PROD_MONGO_HOST/MONGO_HOST is not set.")
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
        return client, coll
    except PyMongoError as e:
        logger.error(f"[search mongo] Error: {e}")
        return None, None
