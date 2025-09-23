from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .scheduler.scheduler import load_arxiv_data_to_dynamodb

app = FastAPI()
scheduler = AsyncIOScheduler()


@app.get("/")
def root():
    return {"Hello World!"}

@app.on_event("startup")
async def startup_event():
    scheduler.add_job(load_arxiv_data_to_dynamodb, 'cron', hour=4, minute=0) # 새벽 4시
    scheduler.start()
    # 앱 시작 시 즉시 1회 실행 (테스트용)
    load_arxiv_data_to_dynamodb()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
