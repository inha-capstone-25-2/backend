## 로컬 세팅

1. `py -3.11 -m venv .venv`
2. `source .venv\Scripts\activate`
3. `python -m pip install --upgrade pip`
4. `pip install -r requirements.txt`

## main 브랜치 push 시 github actions이 실패한다면

1. EC2_HOST를 적절한 퍼블릭 IP 주소로 변경
2. 