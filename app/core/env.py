"""환경변수 로딩 유틸리티.

APP_ENV 값에 따라 적절한 .env 파일을 로드합니다.
"""

from pathlib import Path
import os
from dotenv import load_dotenv


def load_env() -> None:
    """APP_ENV에 따라 환경변수 파일을 로드한다.

    env/<APP_ENV>/.env 파일을 찾아 로드합니다. 파일이 없으면 무시하고,
    이미 설정된 환경변수는 덮어쓰지 않습니다.
    """
    app_env = os.getenv("APP_ENV", "local")
    base_dir = Path(__file__).resolve().parents[2]
    env_path = base_dir / "env" / app_env / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
