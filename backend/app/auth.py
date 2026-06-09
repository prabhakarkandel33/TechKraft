from datetime import datetime, timedelta, timezone
from typing import Optional
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

from app.models import get_db, row_to_user
from app.schemas import TokenData

load_dotenv()

# grabbed these from .env - make sure they're set before running
SECRET_KEY = os.getenv("SECRET_KEY", "changeme-before-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))

# bcrypt is the standard here, tried argon2 briefly but passlib's
# bcrypt support is more straightforward for this scope
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


# ── Password utils ─────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Token creation ─────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    # if no expiry passed in, fall back to the env default
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")

        if not user_id or not email or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token is missing required fields",
            )

        return TokenData(user_id=user_id, email=email, role=role)

    except JWTError:
        # covers expired tokens, bad signature, malformed tokens
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="could not validate token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependencies ────────────────────────────────────
# these get injected into routes via Depends()
# think of them as middleware but scoped to individual endpoints

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenData:
    # pulls the token out of the Authorization: Bearer <token> header
    return decode_token(credentials.credentials)


async def get_current_admin(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    # layered dependency - first checks valid token, then checks role
    # tried doing this inline in routes but it got messy fast
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin access required",
        )
    return current_user


# ── DB helpers for auth routes ──────────────────────────────
# keeping these here so the auth router stays thin

async def get_user_by_email(email: str, db) -> Optional[dict]:
    async with db.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ) as cursor:
        row = await cursor.fetchone()
        return row_to_user(row) if row else None


async def get_user_by_id(user_id: str, db) -> Optional[dict]:
    async with db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return row_to_user(row) if row else None


async def get_user_with_password(email: str, db) -> Optional[dict]:
    # separate from get_user_by_email because we don't want to
    # accidentally expose the password hash in normal user lookups
    async with db.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "password": row["password"],
            "role": row["role"],
            "created_at": row["created_at"],
        }