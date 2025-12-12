"""
arXiv PDF 텍스트 추출기.

arXiv 논문 PDF에서 본문 텍스트를 효율적으로 추출합니다.
PyMuPDF를 사용하여 빠르고 메모리 효율적인 처리를 수행합니다.
"""

import io
import logging
from typing import Optional
import httpx
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# arXiv PDF URL 패턴
ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"

HTTP_TIMEOUT = 30.0


async def fetch_arxiv_pdf_text(arxiv_id: str) -> Optional[str]:
    """
    arXiv 논문 PDF에서 텍스트 추출.

    효율적인 스트리밍 다운로드 및 메모리 내 PDF 처리를 수행합니다.

    Args:
        arxiv_id: arXiv 논문 ID (예: "2401.00001")

    Returns:
        추출된 텍스트 또는 None (실패 시)
    """
    pdf_url = ARXIV_PDF_URL.format(arxiv_id=arxiv_id)

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()

            # PDF 바이트를 메모리에서 처리
            pdf_bytes = response.content
            text = extract_text_from_pdf_bytes(pdf_bytes)

            if text:
                logger.info(f"[PDFExtractor] Extracted {len(text)} chars from {arxiv_id}")
            else:
                logger.warning(f"[PDFExtractor] No text extracted from {arxiv_id}")

            return text

    except httpx.HTTPStatusError as e:
        logger.error(f"[PDFExtractor] HTTP error for {arxiv_id}: {e.response.status_code}")
        return None
    except httpx.TimeoutException:
        logger.error(f"[PDFExtractor] Timeout downloading {arxiv_id}")
        return None
    except Exception as e:
        logger.error(f"[PDFExtractor] Error fetching {arxiv_id}: {e}")
        return None


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    PDF 바이트에서 텍스트 추출 (PyMuPDF 사용).

    메모리 효율적으로 처리하며, 페이지별로 텍스트를 추출합니다.

    Args:
        pdf_bytes: PDF 파일 바이트

    Returns:
        추출된 텍스트
    """
    try:
        # 메모리 스트림에서 PDF 열기
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        text_parts = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")
            if page_text.strip():
                text_parts.append(page_text)
        
        doc.close()

        full_text = "\n".join(text_parts)
        
        full_text = _clean_pdf_text(full_text)

        return full_text

    except Exception as e:
        logger.error(f"[PDFExtractor] PDF parsing error: {e}")
        return ""


def _clean_pdf_text(text: str) -> str:
    """
    PDF에서 추출한 텍스트 정리.

    줄바꿈, 하이픈, 특수 문자 등을 정리합니다.

    Args:
        text: 원본 텍스트

    Returns:
        정리된 텍스트
    """
    import re

    # 줄 끝 하이픈 제거
    text = re.sub(r"-\n", "", text)

    # 연속 줄바꿈을 단락 구분자로 변환
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 단일 줄바꿈을 공백으로
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # 중복 공백 제거
    text = re.sub(r" +", " ", text)

    return text.strip()


def fetch_arxiv_pdf_text_sync(arxiv_id: str) -> Optional[str]:
    """
    arXiv 논문 PDF에서 텍스트 추출 (재시도 포함).

    최대 3회 재시도하며, 실패 시 None 반환.

    Args:
        arxiv_id: arXiv 논문 ID

    Returns:
        추출된 텍스트 또는 None
    """
    import time
    import requests

    pdf_url = ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = requests.get(pdf_url, timeout=HTTP_TIMEOUT, allow_redirects=True)
            response.raise_for_status()

            pdf_bytes = response.content
            text = extract_text_from_pdf_bytes(pdf_bytes)

            if text:
                logger.info(f"[PDFExtractor] Extracted {len(text)} chars from {arxiv_id}")
                if len(text) < 500:
                    logger.warning(f"[PDFExtractor] Short text preview: {text[:200]}...")
            return text

        except requests.Timeout:
            logger.warning(f"[PDFExtractor] Timeout for {arxiv_id}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 지수 백오프
            continue
        except requests.HTTPError as e:
            logger.error(f"[PDFExtractor] HTTP error for {arxiv_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"[PDFExtractor] Error for {arxiv_id}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue

    logger.error(f"[PDFExtractor] All retries failed for {arxiv_id}")
    return None
