from pathlib import Path
import os
from dotenv import load_dotenv

def load_env() -> None:
    """
    APP_ENV(local/prod/...)에 따라 env/<APP_ENV>/.env 로드.
    - 파일이 없으면 조용히 무시
    - 이미 설정된 환경변수는 덮어쓰지 않음(override=False)
    """
    app_env = os.getenv("APP_ENV", "local")
    base_dir = Path(__file__).resolve().parents[2]  # 프로젝트 루트
    env_path = base_dir / "env" / app_env / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)