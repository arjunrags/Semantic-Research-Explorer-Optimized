from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from core.database import get_db
from core.auth import hash_password, verify_password, create_access_token
from core.logging import logger

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing
    result = await db.execute(
        text("SELECT id FROM users WHERE username = :u OR email = :e"),
        {"u": req.username, "e": req.email},
    )
    if result.first():
        raise HTTPException(status_code=409, detail="Username or email already taken")

    hashed = hash_password(req.password)
    await db.execute(
        text("INSERT INTO users (username, email, password_hash) VALUES (:u, :e, :p)"),
        {"u": req.username, "e": req.email, "p": hashed},
    )
    await db.commit()
    logger.info("user_registered", username=req.username)
    return {"status": "created"}


@router.post("/token", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT id, password_hash FROM users WHERE username = :u"),
        {"u": form.username},
    )
    row = result.first()
    if not row or not verify_password(form.password, row[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(str(row[0]))
    logger.info("user_login", username=form.username)
    return {"access_token": token, "token_type": "bearer"}
