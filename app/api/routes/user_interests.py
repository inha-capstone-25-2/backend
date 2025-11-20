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
    codes = list(dict.fromkeys(payload.category_codes))
    if not codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty category_codes"
        )

    categories = db.query(Category).filter(Category.code.in_(codes)).all()
    found_codes = {c.code for c in categories}
    missing = [c for c in codes if c not in found_codes]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"categories not found: {missing}"
        )

    existing = db.query(UserInterest).filter(
        UserInterest.user_id == current_user.id,
        UserInterest.category_id.in_([c.id for c in categories])
    ).all()
    existing_ids = {e.category_id for e in existing}

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

    items: list[InterestItem] = []
    for c in categories:
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
    target_codes = list(dict.fromkeys(codes))
    if not target_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty codes"
        )

    categories = db.query(Category).filter(Category.code.in_(target_codes)).all()
    found_map = {c.code: c for c in categories}
    missing = [c for c in target_codes if c not in found_map]

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