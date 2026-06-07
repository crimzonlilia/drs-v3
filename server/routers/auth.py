"""
Authentication router: register, login, logout, and current user retrieval using Cloudflare D1.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from server.schemas import UserRegister, UserOut, Token
from server.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    TOKEN_BLACKLIST,
    oauth2_scheme,
)
from core.utils.db import execute_query

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister):
    """
    Register a new user account.
    Passwords are encrypted securely using PBKDF2-SHA256.
    """
    username_clean = data.username.strip()
    
    # Check D1 database
    rows = await execute_query("SELECT id FROM users WHERE username = ?", [username_clean])
    if rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
        
    # Store hashed password
    hashed_pwd = get_password_hash(data.password)
    email = data.email.strip() if data.email else None
    created_at = datetime.now().isoformat(timespec="seconds")
    
    await execute_query(
        "INSERT INTO users (username, hashed_password, email, created_at) VALUES (?, ?, ?, ?)",
        [username_clean, hashed_pwd, email, created_at]
    )
    
    return UserOut(username=username_clean, email=email)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login. Access tokens expire in 7 days.
    """
    rows = await execute_query("SELECT hashed_password FROM users WHERE username = ?", [form_data.username])
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = rows[0]
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": form_data.username})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout(token: str = Depends(get_current_user)):
    """
    Log out the current user.
    """
    return {"message": "Successfully logged out"}


@router.post("/logout-token")
async def logout_with_token(token: str = Depends(get_current_user), raw_token: str = Depends(oauth2_scheme)):
    """
    Invalidate the token by placing it in the blacklist.
    """
    TOKEN_BLACKLIST.add(raw_token)
    return {"status": "success", "message": "Token blacklisted successfully"}


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Fetch the profile details of the currently authenticated user.
    """
    return UserOut(username=current_user["username"], email=current_user["email"])
