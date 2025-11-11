## Q. 로컬 개발 환경 세팅 어떻게 하나요

1. `git clone https://github.com/inha-capstone-25-2/backend.git`
2. `cd backend`
3. `py -3.11 -m venv .venv`
4. `source .venv\Scripts\activate`
5. `python -m pip install --upgrade pip`
6. `pip install -r requirements.txt`

## 현 백엔드 레포에서 환경변수가 의미하는 게 뭔가요

- `EC2_HOST` : EC2 퍼블릭 IP 주소
- `EC2_KEY` : pem키
- `EC2_PATH` : fastapi 배포 디렉터리
- `EC2_USER` : EC2 인스턴스 사용자 이름
- `SUBMODULES_SSH_KEY` : 서브모듈 관련 키

## Q. main 브랜치 push/merge 시 github actions이 실패해요

- 환경변수 EC2_HOST를 적절한 퍼블릭 IP 주소로 변경

## Q. 리소스 생성했는데 뭔가 이상해요

- EC2 생성 시 세팅 관련 스크립트가 제대로 수행되었는가 ?
`sudo cat /var/log/cloud-init-output.log`

- Kaggle dataset 로그 관련 스크립트가 제대로 수행되었는가 ?
`sudo cat /var/log/arxiv_sync.log`

- OOM으로 인해 서버가 죽었는가
`sudo dmesg -T | grep -i -E 'killed process|out of memory|oom' || true`

- 현재 서버 메모리 상태가 어떻게 되는가
`free -h`

- 현재 서버의 스왑 메모리 상황이 어떻게 되는가
`swapon --show`

## 
