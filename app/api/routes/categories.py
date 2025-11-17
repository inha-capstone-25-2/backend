from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.models.category import Category, CategoryName
from app.seed.categories_seed import seed_categories

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("/seed")
def seed(force: bool = False, db: Session = Depends(get_db)):
    existing = db.query(Category).count()
    if existing > 0 and not force:
        return {"seeded": False, "reason": "categories already present", "count": existing}
    try:
        seed_categories(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"seed failed: {e}")
    return {
        "seeded": True,
        "categories": db.query(Category).count(),
        "names": db.query(CategoryName).count(),
        "force": force,
    }