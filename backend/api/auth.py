"""
Authentication routes: register, login, me.

Thin layer — all password/token logic lives in security/auth.py.
Login uses OAuth2PasswordRequestForm so the /docs UI "Authorize" button works.

Writes/reads the Supabase "users" table: id UUID, email, password_hash,
full_name, role, created_at. full_name isn't collected by the current
frontend register form — stored as NULL. role defaults to "entrepreneur"
(this endpoint is the self-service founder signup; investor/collaborator
access in the frontend uses its own hardcoded login, unrelated to this table).
"""
import uuid

import psycopg2.extensions
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from database import get_db, db_cursor
from security.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

DEFAULT_ROLE = "entrepreneur"


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: psycopg2.extensions.connection = Depends(get_db)):
    with db_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (%s, %s, %s, %s, %s)",
            (user_id, body.email, hash_password(body.password), body.full_name, DEFAULT_ROLE),
        )
    return {"user_id": user_id, "email": body.email}


@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: psycopg2.extensions.connection = Depends(get_db),
):
    with db_cursor(db) as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (form.username,))
        row = cur.fetchone()
    if row is None or not verify_password(form.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": create_access_token(str(row["id"])),
        "token_type": "bearer",
    }


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user
