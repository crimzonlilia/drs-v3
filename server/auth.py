"""
Secure authentication helper using Python built-in security modules.
Provides PBKDF2 password hashing and dependency-free HS256 JWT tokens.
Stores user records in memory_store/users.json.
"""

import os
import json
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "drs_v3_super_secret_signing_key_change_me_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
USERS_FILE = Path("memory_store/users.json")
TOKEN_BLACKLIST = set()  # In-memory blacklist for logout tokens

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ------------------------------------------------------------------ #
# Built-in Password Hashing (NIST PBKDF2-HMAC-SHA256)                 #
# ------------------------------------------------------------------ #

def get_password_hash(password: str) -> str:
    """
    Generate a secure password hash using PBKDF2.
    Format: iterations$salt$hash (hex encoded)
    """
    salt = os.urandom(16)
    iterations = 100000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the stored PBKDF2 hash.
    """
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        iterations = int(parts[0])
        salt = base64.b64decode(parts[1])
        stored_hash = base64.b64decode(parts[2])
        
        dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, stored_hash)
    except Exception:
        return False


# ------------------------------------------------------------------ #
# Custom Dependency-Free JWT Implementation                           #
# ------------------------------------------------------------------ #

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a standard HS256 JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": int(expire.timestamp())})
    
    # JWT Header & Payload
    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(to_encode).encode("utf-8"))
    
    # Signature
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(sig)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a standard HS256 JWT access token.
    """
    if token in TOKEN_BLACKLIST:
        return None
        
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
            
        header_b64, payload_b64, sig_b64 = parts
        
        # Verify signature
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        expected_sig_b64 = _base64url_encode(expected_sig)
        
        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None
            
        # Parse payload
        payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
        
        # Check expiry
        exp = payload.get("exp")
        if not exp or datetime.utcnow().timestamp() > exp:
            return None
            
        return payload
    except Exception:
        return None


# ------------------------------------------------------------------ #
# User Database Persistence                                           #
# ------------------------------------------------------------------ #

def load_users() -> Dict[str, dict]:
    """
    Load users dictionary from JSON storage.
    """
    if not USERS_FILE.exists():
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_users(users: Dict[str, dict]) -> None:
    """
    Save users dictionary to JSON storage.
    """
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ #
# FastAPI Dependecies                                                 #
# ------------------------------------------------------------------ #

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency to authenticate requests. Extracts user from JWT token.
    """
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = payload.get("sub")
    users = load_users()
    user = users.get(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": username, "email": user.get("email")}
