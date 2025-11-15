from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.models.user import User
from app.models.category import Category
from app.models.user_interest import UserInterest

router = APIRouter(prefix="/user-interests", tags=["user-interests"])

class InterestAddPayload(BaseModel):
    category_codes: list[str] = Field(min_length=1)

class InterestItem(BaseModel):
    code: str
    name_ko: str | None = None
    name_en: str | None = None

class InterestList(BaseModel):
    items: list[InterestItem]

class InterestRemovalResult(BaseModel):
    removed: int
    not_found: list[str]
    remaining: InterestList

@router.post("", status_code=status.HTTP_201_CREATED)
def add_interests(
    payload: InterestAddPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 중복 제거
    codes = list(dict.fromkeys(payload.category_codes))
    if not codes:
        raise HTTPException(400, "empty category_codes")

    categories = db.query(Category).filter(Category.code.in_(codes)).all()
    found_codes = {c.code for c in categories}
    missing = [c for c in codes if c not in found_codes]
    if missing:
        raise HTTPException(404, f"categories not found: {missing}")

    # 이미 있는 관심 조회
    existing = db.query(UserInterest).filter(
        UserInterest.user_id == current_user.id,
        UserInterest.category_id.in_([c.id for c in categories])
    ).all()
    existing_ids = {e.category_id for e in existing}

    # 신규만 추가
    for c in categories:
        if c.id in existing_ids:
            continue
        db.add(UserInterest(user_id=current_user.id, category_id=c.id))

    db.commit()
    return {"added": len(categories) - len(existing_ids), "skipped": len(existing_ids)}

@router.get("", response_model=InterestList)
def list_interests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        db.query(Category)
        .join(UserInterest, UserInterest.category_id == Category.id)
        .filter(UserInterest.user_id == current_user.id)
        .order_by(Category.code.asc())
    )
    categories = q.all()

    # 다국어 이름 선택(ko/en 둘 다 시도)
    items: list[InterestItem] = []
    for c in categories:
        # locale별 이름 조회(메모리상의 relationship 활용)
        name_ko = next((n.name for n in c.names if n.locale == "ko"), None)
        name_en = next((n.name for n in c.names if n.locale == "en"), None)
        items.append(InterestItem(code=c.code, name_ko=name_ko, name_en=name_en))

    return InterestList(items=items)

@router.delete("", response_model=InterestRemovalResult)
def remove_interests(
    codes: list[str] = Query(..., alias="codes", min_length=1, description="삭제할 카테고리 코드(복수 가능)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 중복 제거
    target_codes = list(dict.fromkeys(codes))
    if not target_codes:
        raise HTTPException(400, "empty codes")

    categories = db.query(Category).filter(Category.code.in_(target_codes)).all()
    found_map = {c.code: c for c in categories}
    missing = [c for c in target_codes if c not in found_map]

    # 관심 항목 중 대상
    to_delete = (
        db.query(UserInterest)
        .filter(
            UserInterest.user_id == current_user.id,
            UserInterest.category_id.in_([found_map[c].id for c in found_map])
        )
        .all()
    )
    delete_ids = {ui.category_id for ui in to_delete}

    for ui in to_delete:
        db.delete(ui)
    db.commit()

    # 남은 관심 목록 재조회
    q = (
        db.query(Category)
        .join(UserInterest, UserInterest.category_id == Category.id)
        .filter(UserInterest.user_id == current_user.id)
        .order_by(Category.code.asc())
    )
    remaining_categories = q.all()
    remaining_items = []
    for c in remaining_categories:
        name_ko = next((n.name for n in c.names if n.locale == "ko"), None)
        name_en = next((n.name for n in c.names if n.locale == "en"), None)
        remaining_items.append(InterestItem(code=c.code, name_ko=name_ko, name_en=name_en))

    return InterestRemovalResult(
        removed=len(delete_ids),
        not_found=missing,
        remaining=InterestList(items=remaining_items),
    )

# 기존 단일 삭제 엔드포인트 필요 없으면 주석 처리하거나 제거
# @router.delete("/{category_code}", status_code=status.HTTP_204_NO_CONTENT)
# def remove_interest(...):
#     ...