"""
논문 텍스트 전처리 유틸리티.

arXiv 논문의 텍스트를 정리하고 요약을 위한 전처리를 수행합니다.
"""

import re
from typing import List, Dict


def clean_summary_en(text: str) -> str:
    """
    영문 논문 텍스트 정리.

    LaTeX 명령어, 특수 문자, 이상 패턴 등을 제거합니다.

    Args:
        text: 원본 텍스트

    Returns:
        정리된 텍스트
    """
    if not text:
        return ""

    # <n>을 공백으로 변환
    text = text.replace("<n>", " ")

    # @ 멘션, LaTeX 명령어, $ 기호 제거
    text = re.sub(r"@[a-zA-Z0-9_]+", " ", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = re.sub(r"\$+", " ", text)

    # 섹션 번호 제거
    text = re.sub(r"#\s*\d+", " ", text)

    # LaTeX 그래픽 관련 패턴 제거
    text = re.sub(r"epsf\.tex[^)]*\)", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\([^)]*width[^)]*\)", " ", text, flags=re.IGNORECASE)

    # "section" 단어 제거
    if "section" in text.lower():
        text = re.sub(r"\b[Ss]ection\b", " ", text)

    # 특수 문자 제거
    text = text.replace("[", " ").replace("]", " ")
    text = text.replace("*", " ")
    text = text.replace(",", " ")

    # 빈 괄호 제거
    text = re.sub(r"\(\s*\)", " ", text)

    # 중복 공백 제거
    text = re.sub(r"\s+", " ", text).strip()

    return text


def chunk_text(text: str, max_chars: int = 4000) -> List[str]:
    """
    긴 텍스트를 청크로 분할.

    단락 단위로 분할하여 최대 길이를 초과하지 않도록 합니다.

    Args:
        text: 분할할 텍스트
        max_chars: 청크당 최대 문자 수

    Returns:
        청크 리스트
    """
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    buf = ""

    for p in paragraphs:
        if len(buf) + len(p) + 1 > max_chars:
            if buf:
                chunks.append(buf.strip())
            buf = p
        else:
            buf += ("\n" + p) if buf else p

    if buf:
        chunks.append(buf.strip())

    return chunks


def build_raw_text(doc: Dict) -> str:
    """
    MongoDB 문서에서 원문 텍스트 추출.

    abstract와 본문을 결합하여 전체 텍스트를 생성합니다.

    Args:
        doc: MongoDB 논문 문서

    Returns:
        원문 텍스트
    """
    # summary.en 또는 abstract 필드 사용
    abstract = ""
    if "summary" in doc and isinstance(doc["summary"], dict):
        abstract = doc["summary"].get("en") or ""
    elif "abstract" in doc:
        abstract = doc.get("abstract") or ""

    body = doc.get("text") or ""
    raw_text = (abstract + "\n" + body).strip()

    return raw_text
