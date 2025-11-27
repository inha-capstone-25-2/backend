from __future__ import annotations
import json
import logging
import os
import time
from pathlib import Path
from pymongo import UpdateOne, WriteConcern
from pymongo.errors import BulkWriteError
from app.core.constants import COLLECTION_ARXIV_FAILURES


from app.db.mongodb import get_mongo_client_direct, get_prod_mongo_client, init_mongo
from app.core.settings import settings
from app.loader.arxiv_category import parse_categories
from app.seed.categories_seed import seed_categories_from_codes
from app.seed.bookmarks_seed import seed_bookmarks
from app.seed.activities_seed import seed_activities
from app.seed.papers_enrichment_seed import enrich_papers
from app.seed.search_history_seed import seed_search_history
from app.loader.config import DATA_FILE_PATH, BATCH_SIZE, PROGRESS_EVERY
from app.loader.utils import get_current_time

logger = logging.getLogger(__name__)


def stream_and_insert_data(
    collection, 
    failures_collection, 
    data_file_path: Path, 
    batch_size: int
) -> int:
    """
    스트리밍 방식으로 JSON 파일을 읽고 즉시 배치 삽입.
    메모리에 전체 데이터를 로드하지 않고 배치 단위로 처리.
    """
    batch = []
    count = 0
    start_time = time.time()
    
    logger.info(f"[arxiv-job] 데이터 스트리밍 시작: {data_file_path}")
    
    with open(data_file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            arxiv_id = data.get("id")
            if not arxiv_id:
                continue
            
            # 파싱
            codes = parse_categories(data.get("categories"))
            doc = {
                "_id": arxiv_id,  # arXiv ID를 PK로 사용
                "title": data.get("title"),
                "authors": data.get("authors"),
                "abstract": data.get("abstract"),
                "categories": codes,
                "update_date": data.get("update_date"),
            }
            doc = {k: v for k, v in doc.items() if v is not None}
            batch.append(UpdateOne({"_id": arxiv_id}, {"$set": doc}, upsert=True))
            
            # 배치 크기 도달 시 즉시 삽입
            if len(batch) >= batch_size:
                try:
                    collection.bulk_write(batch, ordered=False)
                    count += len(batch)
                    
                    # 진행상황 로깅 (50,000건마다)
                    if count % 50000 == 0:
                        elapsed = time.time() - start_time
                        rate = count / elapsed if elapsed > 0 else 0
                        logger.info(
                            f"[arxiv-job] 진행: {count:,}건 처리 | "
                            f"속도: {rate:.0f}건/초 | "
                            f"경과시간: {elapsed:.1f}초"
                        )
                    
                    batch.clear()
                except BulkWriteError as bwe:
                    logger.warning(f"[arxiv-job] BulkWriteError: {bwe.details}")
                    # 실패한 문서 기록
                    for e in bwe.details.get("writeErrors", []):
                        if failures_collection:
                            try:
                                failures_collection.insert_one({"_id": e.get("op", {}).get("_id")})
                            except Exception:
                                pass
                    batch.clear()
                except Exception as e:
                    logger.error(f"[arxiv-job] unexpected bulk_write error: {e}")
                    batch.clear()
        
        # 남은 배치 처리
        if batch:
            try:
                collection.bulk_write(batch, ordered=False)
                count += len(batch)
                logger.info(f"[arxiv-job] 남은 배치 처리: {len(batch)}건")
            except BulkWriteError as bwe:
                logger.warning(f"[arxiv-job] BulkWriteError (마지막 배치): {bwe.details}")
            except Exception as e:
                logger.error(f"[arxiv-job] unexpected bulk_write error (마지막 배치): {e}")
    
    total_time = time.time() - start_time
    avg_rate = count / total_time if total_time > 0 else 0
    logger.info(
        f"[arxiv-job] 데이터 삽입 완료: {count:,}건 | "
        f"총 시간: {total_time:.1f}초 | "
        f"평균 속도: {avg_rate:.0f}건/초"
    )
    
    return count


def create_unique_index(collection) -> None:
    """
    고유 인덱스 생성 함수 (deprecated).
    
    _id 필드는 MongoDB가 자동으로 유니크 인덱스를 생성하므로
    별도의 인덱스 생성이 불필요합니다.
    """
    # _id는 자동으로 유니크 인덱스가 생성되므로 skip
    logger.info("[arxiv-job] _id는 자동 인덱스 사용 (별도 생성 불필요)")


def create_text_search_index(collection) -> None:
    """
    전문 검색 인덱스 생성.
    title, abstract, authors 필드에 가중치를 적용한 Text Search 인덱스.
    """
    try:
        collection.create_index(
            [
                ("title", "text"),
                ("abstract", "text"),
                ("authors", "text")
            ],
            weights={
                "title": 10,      # 제목 우선순위 가장 높음
                "abstract": 5,    # 초록
                "authors": 3      # 저자
            },
            default_language="english",
            background=True,  # 백그라운드 빌드 (다운타임 없음)
            name="papers_fulltext_search"
        )
        logger.info("[arxiv-job] Text Search 인덱스 생성 시작 (백그라운드)")
        logger.info("[arxiv-job] 가중치: title=10, abstract=5, authors=3")
    except Exception as e:
        logger.error(f"[arxiv-job] Text Search 인덱스 생성 실패: {e}")


def create_search_indexes(collection) -> None:
    """
    검색용 인덱스 생성 (데이터 삽입 후 실행).
    1. 복합 인덱스: categories + update_date (카테고리 필터 + 날짜 정렬)
    2. Text Search 인덱스: title, abstract, authors (전문 검색)
    """
    try:
        # 1. 복합 인덱스: 카테고리 필터 + 날짜 정렬
        collection.create_index(
            [("categories", 1), ("update_date", -1)],
            name="categories_update_date"
        )
        logger.info("[arxiv-job] 복합 인덱스 생성 완료: categories + update_date")
        
        # 2. Text Search 인덱스
        create_text_search_index(collection)
        
    except Exception as e:
        logger.error(f"[arxiv-job] 검색 인덱스 생성 실패: {e}")


def seed_categories_from_mongo(collection) -> None:
    """
    MongoDB의 카테고리 코드를 기반으로 PostgreSQL 시드.
    """
    unique_codes = set()
    cursor = collection.find({}, {"categories": 1})
    for doc in cursor:
        if "categories" in doc and isinstance(doc["categories"], list):
            unique_codes.update(doc["categories"])
    cursor.close()
    if unique_codes:
        logger.info(f"[arxiv-job] seeding PostgreSQL categories from {len(unique_codes)} codes")
        try:
            seed_categories_from_codes(list(unique_codes))
        except Exception as e:
            logger.error(f"[arxiv-job] category seeding failed: {e}")


def run_mock_seeding(db) -> None:
    """
    Mock 데이터 시딩 (Enrichment, Bookmarks, Activities, SearchHistory).
    데이터 적재 완료 후 실행됩니다.
    """
    logger.info("[arxiv-job] Starting mock data seeding...")
    try:
        # 1. Papers Enrichment (필수: view_count 등이 있어야 정렬 가능)
        logger.info("[arxiv-job] Enriching papers (view_count, embeddings)...")
        enrich_papers(db)

        # 2. Bookmarks 시딩
        logger.info("[arxiv-job] Seeding bookmarks...")
        seed_bookmarks(db)
        
        # 3. Activities 시딩
        logger.info("[arxiv-job] Seeding user activities...")
        seed_activities(db)
        
        # 4. Search History 시딩
        logger.info("[arxiv-job] Seeding search history...")
        seed_search_history(db)
        
        logger.info("[arxiv-job] Mock data seeding completed successfully.")
    except Exception as e:
        logger.error(f"[arxiv-job] Mock data seeding failed: {e}")


def ingest_arxiv_to_mongo() -> bool:
    """
    arXiv 데이터를 MongoDB에 적재 (최적화된 버전).
    """
    try:
        client = get_mongo_client_direct()
    except RuntimeError:
        # 백그라운드 작업 등에서 초기화되지 않은 경우
        logger.info("[arxiv-job] MongoDB not initialized, initializing now...")
        init_mongo()
        try:
            client = get_mongo_client_direct()
        except RuntimeError as e:
            logger.error(f"[arxiv-job] MongoDB initialization failed: {e}")
            return False

    db = client[settings.mongo_db]
    collection = db[settings.mongo_collection]
    failures_collection = db[COLLECTION_ARXIV_FAILURES]
    
    # WriteConcern 최적화 (빠른 쓰기)
    collection = collection.with_options(
        write_concern=WriteConcern(w=1, j=False)
    )
    
    logger.info(f"[arxiv-job] MongoDB collection: {collection.full_name}")

    # 기존 데이터 삭제 (옵션)
    if os.getenv("ARXIV_REMOVE_OLD_DATA"):
        logger.info("[arxiv-job] removing old data")
        collection.delete_many({})

    # 1. 고유 인덱스만 먼저 생성 (중복 방지용) - _id는 자동이므로 skip
    create_unique_index(collection)

    try:
        # 2. 데이터 스트리밍 삽입
        logger.info("[arxiv-job] 데이터 적재 시작 (스트리밍 방식)")
        count = stream_and_insert_data(
            collection, 
            failures_collection, 
            DATA_FILE_PATH, 
            BATCH_SIZE
        )
        logger.info(f"[arxiv-job] 데이터 적재 완료: {count:,}건")
        
        # 3. 검색용 인덱스 생성 (데이터 삽입 후)
        logger.info("[arxiv-job] 검색 인덱스 생성 시작")
        create_search_indexes(collection)
        logger.info("[arxiv-job] 검색 인덱스 생성 완료")
        
        # 4. PostgreSQL 카테고리 시딩
        seed_categories_from_mongo(collection)
        
        # 5. Mock 데이터 시딩 (자동 실행)
        run_mock_seeding(db)
        
        return True
    except FileNotFoundError:
        logger.error(f"[arxiv-job] file not found: {DATA_FILE_PATH}")
    except json.JSONDecodeError as e:
        logger.error(f"[arxiv-job] JSON decode error: {e}")
    except Exception as e:
        logger.error(f"[arxiv-job] unexpected error: {e}")
    return False


def copy_prod_to_local_mongo() -> bool:
    """
    Production MongoDB에서 로컬 MongoDB로 arxiv_papers 데이터 복제.
    복제 완료 후 카테고리 시딩 및 Mock 데이터 시딩을 수행.
    """
    logger.info("[arxiv-job] Starting data copy from production to local MongoDB")
    
    # Production MongoDB 연결
    try:
        prod_client = get_prod_mongo_client()
    except RuntimeError as e:
        logger.error(f"[arxiv-job] Failed to connect to production MongoDB: {e}")
        return False
    except Exception as e:
        logger.error(f"[arxiv-job] Unexpected error connecting to production: {e}")
        return False

    # Local MongoDB 연결
    try:
        local_client = get_mongo_client_direct()
    except RuntimeError:
        # 백그라운드 작업 등에서 초기화되지 않은 경우
        logger.info("[arxiv-job] Local MongoDB not initialized, initializing now...")
        init_mongo()
        try:
            local_client = get_mongo_client_direct()
        except RuntimeError as e:
            logger.error(f"[arxiv-job] Local MongoDB initialization failed: {e}")
            if prod_client:
                prod_client.close()
            return False

    try:
        # Production 컬렉션
        prod_db = prod_client[settings.prod_mongo_db]
        prod_coll = prod_db[settings.prod_mongo_collection]
        
        # Local 컬렉션
        local_db = local_client[settings.mongo_db]
        local_coll = local_db[settings.mongo_collection]

        logger.info(f"[arxiv-job] Source: {prod_coll.full_name}")
        logger.info(f"[arxiv-job] Destination: {local_coll.full_name}")

        # 로컬 컬렉션 초기화
        logger.info("[arxiv-job] Clearing local collection")
        local_coll.delete_many({})

        # 데이터 복제
        logger.info("[arxiv-job] Starting data copy...")
        cursor = prod_coll.find({}, no_cursor_timeout=True)
        batch = []
        BATCH_SIZE = 1000
        count = 0

        try:
            for doc in cursor:
                # 기존 ObjectId인 _id 제거
                doc.pop("_id", None)
                # id 필드가 있으면 _id로 변환 (arXiv ID)
                if "id" in doc:
                    doc["_id"] = doc.pop("id")
                batch.append(doc)
                
                if len(batch) >= BATCH_SIZE:
                    local_coll.insert_many(batch)
                    count += len(batch)
                    logger.info(f"[arxiv-job] Copied {count} documents so far...")
                    batch.clear()
            
            # 남은 배치 처리
            if batch:
                local_coll.insert_many(batch)
                count += len(batch)
                logger.info(f"[arxiv-job] Copied final batch. Total: {count} documents")
        finally:
            cursor.close()

        logger.info(f"[arxiv-job] Data copy complete: total {count} documents")

        # 카테고리 시딩
        logger.info("[arxiv-job] Starting category seeding...")
        seed_categories_from_mongo(local_coll)
        logger.info("[arxiv-job] Category seeding complete")
        
        # Mock 데이터 시딩 (자동 실행)
        run_mock_seeding(local_db)

        return True

    except Exception as e:
        logger.error(f"[arxiv-job] Copy failed: {e}")
        return False
    finally:
        # Production 클라이언트는 반드시 닫아야 함 (임시 연결)
        if prod_client:
            prod_client.close()
            logger.info("[arxiv-job] Production MongoDB connection closed")