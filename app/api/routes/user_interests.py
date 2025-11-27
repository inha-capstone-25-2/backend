from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.user_interest import (
    InterestAddPayload,
    InterestList,
    InterestRemovalResult,
)
from app.services.user_interest_service import UserInterestService

router = APIRouter(prefix="/user-interests", tags=["user-interests"])


@router.post("", status_code=status.HTTP_201_CREATED)
def add_interests(
    payload: InterestAddPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """사용자 관심사 추가."""
    service = UserInterestService(db)
    return service.add_interests(current_user, payload.category_codes)


@router.get("", response_model=InterestList)
def list_interests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """사용자 관심사 목록 조회."""
    service = UserInterestService(db)
    return service.list_interests(current_user)


@router.delete("", response_model=InterestRemovalResult)
def remove_interests(
    codes: list[str] = Query(
        ..., alias="codes", min_length=1, description="삭제할 카테고리 코드(복수 가능)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """사용자 관심사 삭제."""
    service = UserInterestService(db)
    return service.remove_interests(current_user, codes)
