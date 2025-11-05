import gzip
import os
from pathlib import Path
from pymongo import UpdateOne
from pymongo.errors import PyMongoError
from rdflib import Graph, URIRef, Literal, RDF
from rdflib.namespace import XSD, RDFS

from app.core.env import load_env
load_env()  # APP_ENV에 맞는 .env 로드

from app.db.connection import get_mongo_collection

DB_NAME = os.getenv("MONGO_DB", "dblp")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "publications")
NT_FILE_PATH = "./data/dblp.nt.gz"
SCHEMA_FILE_PATH = "./data/schema-2024-06-14.rdf"
BATCH_SIZE = 50000 # 버퍼 크기를 늘려 I/O 효율 개선

# 스키마에서 사용할 주요 클래스와 프로퍼티 정의
DBLP_NS = "https://dblp.org/rdf/schema#"
PUBLICATION = URIRef(f"{DBLP_NS}Publication")

# MongoDB 필드명으로 사용할 predicate와 다중값 여부 매핑
# 스키마를 분석하여 필요한 속성들을 미리 정의합니다.
PREDICATE_MAP = {
    URIRef(f"{DBLP_NS}title"): {"field": "title", "multi": False},
    URIRef("http://purl.org/dc/elements/1.1/creator"): {"field": "creators", "multi": True},
    URIRef(f"{DBLP_NS}authoredBy"): {"field": "authors", "multi": True},
    URIRef(f"{DBLP_NS}editedBy"): {"field": "editors", "multi": True},
    URIRef(f"{DBLP_NS}yearOfPublication"): {"field": "year", "multi": False},
    URIRef(f"{DBLP_NS}pagination"): {"field": "pages", "multi": False},
    URIRef(f"{DBLP_NS}publishedIn"): {"field": "published_in", "multi": False},
    URIRef(f"{DBLP_NS}doi"): {"field": "doi", "multi": False},
    URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"): {"field": "type", "multi": True},
}

def cast_type(value: Literal):
    """rdflib Literal 객체를 데이터 타입에 맞게 Python 타입으로 변환합니다."""
    if value.datatype in [XSD.gYear, XSD.integer]:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if value.datatype in [XSD.date, XSD.dateTime]:
        return value.toPython()
    # 그 외의 경우는 문자열로 처리
    return str(value)

# 수정: MongoSink를 Graph를 상속받는 MongoGraph로 변경
class MongoGraph(Graph):
    """
    RDF 트리플을 스트리밍으로 받아 MongoDB 문서로 변환하고 bulk-write하는 Graph.
    메모리에 트리플을 저장하지 않고 바로 처리합니다.
    """
    def __init__(self, collection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection = collection
        self.buffer = {}
        self.count = 0
        self.is_publication = {}

    def add(self, triple):
        s, p, o = triple
        # Publication 타입인지 먼저 확인
        if p == RDF.type and o == PUBLICATION:
            self.is_publication[s] = True

        # PREDICATE_MAP에 없는 속성은 무시
        if p not in PREDICATE_MAP:
            return self

        # Publication 타입인 주제만 버퍼에 추가
        if s not in self.is_publication or not self.is_publication.get(s):
            return self

        doc_id = str(s)
        if doc_id not in self.buffer:
            self.buffer[doc_id] = {'_id': doc_id}

        mapping = PREDICATE_MAP[p]
        field = mapping["field"]
        value = cast_type(o) if isinstance(o, Literal) else str(o)
        if value is None:
            return self

        if mapping["multi"]:
            if field not in self.buffer[doc_id]:
                self.buffer[doc_id][field] = []
            self.buffer[doc_id][field].append(value)
        else:
            self.buffer[doc_id][field] = value
        
        self.count += 1
        if self.count % (BATCH_SIZE * 5) == 0: # 약 5배수 트리플마다 로그 출력
            print(f"Processed {self.count} triples, buffer size: {len(self.buffer)}")

        # 버퍼가 가득 차면 MongoDB에 쓰고 비움
        if len(self.buffer) >= BATCH_SIZE:
            self.flush()
        
        return self # Graph.add는 self를 반환해야 함

    def flush(self):
        if not self.buffer:
            return
        print(f"Flushing buffer with {len(self.buffer)} documents...")
        try:
            operations = [UpdateOne({'_id': d['_id']}, {'$set': d}, upsert=True) for d in self.buffer.values()]
            self.collection.bulk_write(operations, ordered=False)
        except PyMongoError as e:
            print(f"Mongo bulk_write error: {e}")
        self.buffer.clear()
        # is_publication은 계속 유지해야 다음 트리플 처리 가능. flush 시 비우지 않음.
        # 단, 메모리 관리가 필요하면 주기적으로 오래된 키를 삭제하는 로직 추가 가능

def parse_and_load(data_filepath, schema_filepath):
    client, collection = get_mongo_collection()
    if client is None or collection is None:
        print("Mongo 연결 실패. 환경변수 설정을 확인하세요.")
        return

    if not os.path.exists(data_filepath):
        print(f"오류: 데이터 파일({data_filepath})을 찾을 수 없습니다.")
        return

    print("Stream parsing and loading process started...")
    # 수정: MongoGraph 인스턴스를 생성
    mongo_sink_graph = MongoGraph(collection)

    try:
        # 수정: MongoGraph의 parse 메서드를 직접 호출하여 스트림 파싱
        with gzip.open(data_filepath, 'rb') as f:
            mongo_sink_graph.parse(f, format="nt")
        
        # 마지막 남은 버퍼 처리
        mongo_sink_graph.flush()
        print("All tasks completed.")

    except Exception as e:
        print(f"An error occurred during parsing: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    parse_and_load(NT_FILE_PATH, SCHEMA_FILE_PATH)
