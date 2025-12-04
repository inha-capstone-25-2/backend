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

    단락 단위로 분할하되, 단락이 max_chars를 초과하면 문장 단위로 추가 분할합니다.

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
        # 단일 단락이 max_chars를 초과하는 경우 문장 단위로 분할
        if len(p) > max_chars:
            # 현재 버퍼가 있으면 먼저 저장
            if buf:
                chunks.append(buf.strip())
                buf = ""
            
            # 문장 단위로 분할 (마침표, 물음표, 느낌표 기준)
            sentences = re.split(r'(?<=[.!?])\s+', p)
            sentence_buf = ""
            
            for sentence in sentences:
                if len(sentence_buf) + len(sentence) + 1 > max_chars:
                    if sentence_buf:
                        chunks.append(sentence_buf.strip())
                    # 단일 문장이 max_chars 초과 시 강제 분할
                    if len(sentence) > max_chars:
                        for i in range(0, len(sentence), max_chars):
                            chunks.append(sentence[i:i + max_chars].strip())
                        sentence_buf = ""
                    else:
                        sentence_buf = sentence
                else:
                    sentence_buf += (" " + sentence) if sentence_buf else sentence
            
            if sentence_buf:
                buf = sentence_buf
        elif len(buf) + len(p) + 1 > max_chars:
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

    summary.en(Abstract)만 반환합니다.
    본문은 PDF에서 추출해야 하므로 별도 처리 필요.

    Args:
        doc: MongoDB 논문 문서

    Returns:
        Abstract 텍스트
    """
    # summary.en 필드 사용 (Abstract)
    abstract = ""
    if "summary" in doc and isinstance(doc["summary"], dict):
        abstract = doc["summary"].get("en") or ""

    return abstract.strip()


def build_full_text_with_pdf(doc: Dict, pdf_text: str) -> str:
    """
    Abstract와 PDF 본문을 결합하여 전체 텍스트 생성.

    Args:
        doc: MongoDB 논문 문서
        pdf_text: PDF에서 추출한 본문 텍스트

    Returns:
        전체 텍스트 (Abstract + 본문)
    """
    abstract = build_raw_text(doc)
    
    if abstract and pdf_text:
        return f"{abstract}\n\n{pdf_text}"
    elif pdf_text:
        return pdf_text
    else:
        return abstract
