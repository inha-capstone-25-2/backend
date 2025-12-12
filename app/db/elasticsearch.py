"""
Elasticsearch 데이터베이스 연결 설정.

Elasticsearch 클라이언트를 초기화하고 연결을 관리합니다.
"""

import logging
from typing import Generator
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError, ApiError

from app.core.settings import settings

logger = logging.getLogger(__name__)

_es_client: Elasticsearch | None = None


def get_elasticsearch_client() -> Elasticsearch:
    """
    Elasticsearch 클라이언트 싱글톤을 반환합니다.
    
    Returns:
        Elasticsearch: Elasticsearch 클라이언트 인스턴스
        
    Raises:
        ESConnectionError: Elasticsearch 연결 실패 시
    """
    global _es_client
    
    if _es_client is None:
        host_url = settings.es_host
        port = settings.es_port
        
        scheme = "https" if settings.es_use_ssl else "http"
        host = f"{scheme}://{host_url}:{port}"
        
        if settings.es_user and settings.es_password:
            _es_client = Elasticsearch(
                hosts=[host],
                basic_auth=(settings.es_user, settings.es_password),
                verify_certs=settings.es_use_ssl,
            )
        else:
            _es_client = Elasticsearch(
                hosts=[host],
                verify_certs=settings.es_use_ssl,
            )
        
        try:
            if not _es_client.ping():
                logger.error(f"[ES] Failed to ping Elasticsearch at {host}")
                try:
                    _es_client.info()
                except (ESConnectionError, ApiError) as e:
                    logger.error(f"[ES] Connection diagnosis: {e}")
                    if hasattr(e, "body"):
                        logger.error(f"[ES] Error body: {e.body}")
                
                raise ESConnectionError(f"Cannot connect to Elasticsearch at {host}")
            
            logger.info(f"[ES] Successfully connected to Elasticsearch at {host}")
            
            info = _es_client.info()
            logger.info(f"[ES] Cluster name: {info.get('cluster_name', 'unknown')}")
            logger.info(f"[ES] Version: {info.get('version', {}).get('number', 'unknown')}")
            
        except (ESConnectionError, ApiError) as e:
            logger.error(f"[ES] Elasticsearch connection error: {e}")
            _es_client = None
            raise ESConnectionError(f"Elasticsearch connection failed: {e}")
    
    return _es_client


def get_es() -> Generator[Elasticsearch, None, None]:
    """
    FastAPI dependency용 Elasticsearch 클라이언트를 반환합니다.
    
    Yields:
        Elasticsearch: Elasticsearch 클라이언트 인스턴스
    """
    try:
        client = get_elasticsearch_client()
        yield client
    except ESConnectionError as e:
        logger.error(f"[ES] Dependency injection failed: {e}")
        yield None


def close_elasticsearch():
    """
    Elasticsearch 연결을 닫습니다.
    애플리케이션 종료 시 호출됩니다.
    """
    global _es_client
    
    if _es_client is not None:
        _es_client.close()
        logger.info("[ES] Elasticsearch connection closed")
        _es_client = None


def check_elasticsearch_health() -> dict:
    """
    Elasticsearch 클러스터의 헬스 상태를 확인합니다.
    
    Returns:
        dict: 헬스 정보 딕셔너리
        
    Example:
        {
            "status": "green",
            "cluster_name": "my-cluster",
            "number_of_nodes": 3
        }
    """
    try:
        client = get_elasticsearch_client()
        health = client.cluster.health()
        
        return {
            "status": health.get("status", "unknown"),
            "cluster_name": health.get("cluster_name", "unknown"),
            "number_of_nodes": health.get("number_of_nodes", 0),
            "number_of_data_nodes": health.get("number_of_data_nodes", 0),
            "active_primary_shards": health.get("active_primary_shards", 0),
            "active_shards": health.get("active_shards", 0),
        }
    except (ESConnectionError, ApiError) as e:
        logger.error(f"[ES] Health check failed: {e}")
        return {
            "status": "unavailable",
            "error": str(e),
        }


def init_elasticsearch() -> None:
    """
    애플리케이션 시작 시 Elasticsearch 초기화.
    인덱스 존재 여부를 확인하고 매핑을 업데이트합니다.
    """
    try:
        client = get_elasticsearch_client()
        from app.repositories.elasticsearch_repository import ElasticsearchRepository
        
        repo = ElasticsearchRepository(client)
        repo.update_mapping()
        
    except (ESConnectionError, ApiError) as e:
        logger.error(f"[ES] Initialization failed: {e}")
