from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_password_hash, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import UserRegister, UserLogin, Token, UserOut, OnboardingComplete, OnboardingUpdate
from app.utils import to_json_list, from_json_list

router = APIRouter(prefix="/auth", tags=["auth"])


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        onboarding_completed=user.onboarding_completed,
        subjects=from_json_list(user.subjects),
        grade_levels=from_json_list(user.grade_levels),
        teaching_format=user.teaching_format or "",
    )


@router.post("/register", response_model=Token)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        name=data.name or data.email.split("@")[0],
        onboarding_completed=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_to_out(user)


@router.post("/onboarding", response_model=UserOut)
def complete_onboarding(
    data: OnboardingComplete,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.subjects = to_json_list(data.subjects)
    user.grade_levels = to_json_list(data.grade_levels)
    user.teaching_format = data.teaching_format or ""
    user.onboarding_completed = True
    db.commit()
    db.refresh(user)
    return user_to_out(user)


@router.put("/profile", response_model=UserOut)
def update_profile(
    data: OnboardingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.subjects is not None:
        user.subjects = to_json_list(data.subjects)
    if data.grade_levels is not None:
        user.grade_levels = to_json_list(data.grade_levels)
    if data.teaching_format is not None:
        user.teaching_format = data.teaching_format
    db.commit()
    db.refresh(user)
    return user_to_out(user)
