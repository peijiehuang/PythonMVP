from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from core.config import settings
from core.database import get_session
from core.security import verify_password, create_access_token, get_current_user
from models.models import User, UserRead, Token

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=400, # Consistent with previous implementation
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
