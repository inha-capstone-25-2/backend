from .db.connection import get_mysql_connection, get_dynamodb_resource
from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.get("/")
def root():
    return {"Hello World!"}
