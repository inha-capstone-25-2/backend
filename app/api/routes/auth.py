from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import timedelta
from app.api.deps import get_current_user
from fastapi import Query  # 추가

from app.db.postgres import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserOut, Token, UsernameExists  # 추가
from app.core.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(User).filter(
        or_(User.email == payload.email, User.username == payload.username)
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    user = User(
        email=payload.email,
        username=payload.username,
        name=payload.name,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # username 필드만 사용
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(
        data={"sub": user.username},  # sub에 username 저장
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/username-exists", response_model=UsernameExists)
def username_exists(
    username: str = Query(min_length=3, max_length=50),
    db: Session = Depends(get_db),
) -> UsernameExists:
    """중복 아이디 존재 여부 조회(비인증)."""
    exists = db.query(User.id).filter(User.username == username).first() is not None
    return UsernameExists(exists=exists)

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user