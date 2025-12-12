"""
논문 텍스트 전처리 유틸리티.

arXiv 논문의 텍스트를 정리하고 요약을 위한 전처리를 수행합니다.
"""

from typing import Dict


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
