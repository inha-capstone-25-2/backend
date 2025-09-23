from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .scheduler.scheduler import load_arxiv_data_to_dynamodb

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 실행
    scheduler.add_job(load_arxiv_data_to_dynamodb, 'cron', hour=4, minute=0) # 새벽 4시
    scheduler.start()
    # 앱 시작 시 즉시 1회 실행 (테스트용)
    load_arxiv_data_to_dynamodb()
    
    yield
    
    # 애플리케이션 종료 시 실행
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"Hello World!"}
