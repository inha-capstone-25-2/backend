import json
import logging
import os
import subprocess
import zipfile
from ..db.connection import get_dynamodb_resource

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE_NAME = "arxiv_papers"
DATA_DIR = "/app/data"
DATA_FILE_PATH = os.path.join(DATA_DIR, "arxiv-metadata-oai-snapshot.json")
ZIP_FILE_PATH = os.path.join(DATA_DIR, "arxiv.zip")


def download_and_unzip_dataset():
    logger.info("Starting dataset download from Kaggle.")

    # 다운받은 JSON 파일 경로
    os.makedirs(DATA_DIR, exist_ok=True)

    # Kaggle API를 사용하여 데이터셋 다운로드
    try:
        subprocess.run(
            [
                "kaggle", "datasets", "download",
                "Cornell-University/arxiv",
                "-p", DATA_DIR,
                "--unzip"
            ],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Dataset downloaded and unzipped successfully.")
        
        # 압축 해제 후 삭제
        if os.path.exists(ZIP_FILE_PATH):
            os.remove(ZIP_FILE_PATH)
            logger.info(f"Removed zip file: {ZIP_FILE_PATH}")

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to download or unzip dataset: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("`kaggle` command not found. Is it installed in the Docker container?")
        return False


def create_arxiv_table(dynamodb):
    try:
        existing_tables = [table.name for table in dynamodb.tables.all()]
        if TABLE_NAME not in existing_tables:
            logger.info(f"Creating table: {TABLE_NAME}")
            table = dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            table.wait_until_exists()
            logger.info(f"Table {TABLE_NAME} created successfully.")
        else:
            logger.info(f"Table {TABLE_NAME} already exists.")
        return dynamodb.Table(TABLE_NAME)
    except Exception as e:
        logger.error(f"Error creating table: {e}")
        return None


def load_arxiv_data_to_dynamodb():
    logger.info("Starting arXiv data load job.")

    # 데이터셋 다운로드 및 압축 해제
    if not download_and_unzip_dataset():
        logger.error("Aborting data load job due to download failure.")
        return

    # DynamoDB에 데이터 로드
    dynamodb = get_dynamodb_resource()
    if not dynamodb:
        logger.error("Failed to get DynamoDB resource. Aborting job.")
        return

    table = create_arxiv_table(dynamodb)
    if not table:
        logger.error("Failed to get DynamoDB table. Aborting job.")
        return

    try:
        with open(DATA_FILE_PATH, 'r') as f, table.batch_writer() as batch:
            count = 0
            for line in f:
                try:
                    data = json.loads(line)
                    # 필요한 데이터만 선택하여 저장
                    item = {
                        'id': data.get('id'),
                        'title': data.get('title'),
                        'authors': data.get('authors'),
                        'abstract': data.get('abstract'),
                        'categories': data.get('categories'),
                        'update_date': data.get('update_date')
                    }
                    # None 값 필드 제거
                    item = {k: v for k, v in item.items() if v is not None}

                    if item.get('id'):
                        batch.put_item(Item=item)
                        count += 1
                        if count % 5000 == 0:
                            logger.info(f"Loaded {count} items into DynamoDB.")
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode JSON for line: {line.strip()}")
                    continue
        logger.info(f"Finished loading data. Total items loaded: {count}")
    except FileNotFoundError:
        logger.error(
            f"Data file not found at {DATA_FILE_PATH}. Please make sure the file exists and the volume is mounted correctly.")
    except Exception as e:
        logger.error(f"An error occurred during data loading: {e}")
