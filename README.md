## 로컬 세팅

1. `py -3.11 -m venv .venv`
2. `source .venv\Scripts\activate`
3. `python -m pip install --upgrade pip`
4. `pip install -r requirements.txt`

## kaggle dataset 수동 다운로드

1. ~/.kaggle 에 kaggle.json 저장
2. POST http://localhost:8000/jobs/arxiv/run 호출