from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import timedelta

from app.db.postgres import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserOut, Token, UsernameExists
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.settings import settings
from app.api.deps import get_current_user

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
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(
        data={
            "sub": user.username,
            "ver": user.token_version or 0
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/username-exists", response_model=UsernameExists)
def username_exists(
    username: str = Query(min_length=3, max_length=50),
    db: Session = Depends(get_db),
) -> UsernameExists:
    exists = db.query(User.id).filter(User.username == username).first() is not None
    return UsernameExists(exists=exists)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.token_version = (current_user.token_version or 0) + 1
    db.add(current_user)
    db.commit()
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    resp.delete_cookie("access_token")
    resp.delete_cookie("refreshToken")
    return resp


@router.delete("/quit", status_code=status.HTTP_204_NO_CONTENT)
def quit_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.delete(current_user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)