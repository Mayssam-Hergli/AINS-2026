"""
Authentication routes: register, login, me.

Thin layer — all password/token logic lives in security/auth.py.
Login uses OAuth2PasswordRequestForm so the /docs UI "Authorize" button works.
"""
import uuid
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from database import get_db
from security.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: sqlite3.Connection = Depends(get_db)):
    if db.execute("SELECT id FROM users WHERE email = ?", (body.email,)).fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (id, email, hashed_password) VALUES (?, ?, ?)",
        (user_id, body.email, hash_password(body.password)),
    )
    return {"user_id": user_id, "email": body.email}


@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute("SELECT * FROM users WHERE email = ?", (form.username,)).fetchone()
    if row is None or not verify_password(form.password, row["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": create_access_token(row["id"]),
        "token_type": "bearer",
    }


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user
