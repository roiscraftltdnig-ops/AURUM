from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from urllib.parse import quote
from app.core.security import create_access_token, verify_password
from app.db.supabase import supabase

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
async def login(payload: LoginRequest) -> dict[str, str]:
    if not supabase.ready():
        if payload.email == "admin@roiscraft.ai" and payload.password == "ChangeMeNow!2026":
            token = create_access_token("local-admin", "owner")
            return {"access_token": token, "token_type": "bearer", "role": "owner"}
        raise HTTPException(status_code=401, detail="Invalid local development credentials")
    rows = await supabase.select("admin_users", f"email=eq.{quote(payload.email)}", limit=1)
    if not rows or not verify_password(payload.password, rows[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(rows[0]["id"], rows[0]["role"])
    return {"access_token": token, "token_type": "bearer", "role": rows[0]["role"]}
