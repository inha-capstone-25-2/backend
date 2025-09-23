# Python 3.9 공식 이미지를 기반으로 함
FROM python:3.9-slim

# curl, unzip 설치
RUN apt-get update && apt-get install -y curl unzip && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Kaggle API 인증 설정
COPY kaggle.json /root/.kaggle/
RUN chmod 600 /root/.kaggle/kaggle.json

# 의존성 파일 복사 및 설치
COPY ./requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
