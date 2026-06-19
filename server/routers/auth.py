"""
Authentication router: register, login, logout, and current user retrieval using Cloudflare D1.
"""

import os
import httpx
import uuid
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse

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


# ------------------------------------------------------------------ #
# Google SSO & Mock SSO Endpoints                                   #
# ------------------------------------------------------------------ #

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:3000/login/callback")

class CallbackRequest(BaseModel):
    code: str

@router.get("/google/login")
async def google_login():
    """
    Get Google OAuth2 Authorization URL.
    Falls back to mock consent screen if client ID is missing.
    """
    if GOOGLE_CLIENT_ID:
        url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={GOOGLE_CLIENT_ID}"
            f"&redirect_uri={GOOGLE_REDIRECT_URI}"
            "&response_type=code"
            "&scope=openid%20email%20profile"
        )
    else:
        url = f"http://127.0.0.1:8000/api/auth/mock-sso/google?redirect_uri={GOOGLE_REDIRECT_URI}"
    
    return {"url": url}

@router.get("/mock-sso/google", response_class=HTMLResponse)
async def mock_google_sso_page(redirect_uri: str):
    """
    Renders a premium Google Consent screen for Mock SSO testing.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mock Google Sign-In</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Outfit', sans-serif;
            }}
            body {{
                background: #0f172a;
                color: #f8fafc;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                padding: 20px;
            }}
            .card {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 24px;
                padding: 40px;
                width: 100%;
                max-width: 440px;
                box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.3), 0 8px 10px -6px rgb(0 0 0 / 0.3);
                text-align: center;
                animation: fadeIn 0.4s ease-out;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: scale(0.95); }}
                to {{ opacity: 1; transform: scale(1); }}
            }}
            .logo-container {{
                display: flex;
                justify-content: center;
                margin-bottom: 24px;
            }}
            .google-logo {{
                width: 48px;
                height: 48px;
            }}
            h1 {{
                font-size: 24px;
                font-weight: 600;
                color: #f1f5f9;
                margin-bottom: 12px;
            }}
            .subtitle {{
                font-size: 14px;
                color: #94a3b8;
                margin-bottom: 32px;
                line-height: 1.5;
            }}
            .user-profile {{
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 16px;
                padding: 16px;
                display: flex;
                align-items: center;
                gap: 16px;
                margin-bottom: 32px;
                text-align: left;
                cursor: pointer;
                transition: all 0.2s ease;
                text-decoration: none;
            }}
            .user-profile:hover {{
                border-color: #6366f1;
                background: #1e1b4b;
            }}
            .avatar {{
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: #6366f1;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 18px;
            }}
            .user-info {{
                display: flex;
                flex-direction: column;
            }}
            .name {{
                font-weight: 500;
                color: #e2e8f0;
                font-size: 15px;
            }}
            .email {{
                font-size: 13px;
                color: #64748b;
            }}
            .btn {{
                display: inline-block;
                width: 100%;
                background: #6366f1;
                color: white;
                border: none;
                border-radius: 14px;
                padding: 14px;
                font-weight: 600;
                font-size: 15px;
                cursor: pointer;
                transition: background 0.2s;
                text-decoration: none;
                box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            }}
            .btn:hover {{
                background: #4f46e5;
            }}
            .cancel-link {{
                display: block;
                margin-top: 16px;
                font-size: 14px;
                color: #94a3b8;
                text-decoration: none;
            }}
            .cancel-link:hover {{
                color: #e2e8f0;
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="logo-container">
                <svg class="google-logo" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.77c-.98.66-2.23 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
            </div>
            <h1>Đăng nhập bằng Google (Mock SSO)</h1>
            <p class="subtitle">Ứng dụng <b>DRS v3</b> yêu cầu quyền truy cập thông tin email và hồ sơ công khai của bạn.</p>
            
            <a href="{redirect_uri}?code=mock_google_123&provider=google" class="user-profile">
                <div class="avatar">G</div>
                <div class="user-info">
                    <span class="name">Mock Google User</span>
                    <span class="email">mock.google.user@gmail.com</span>
                </div>
            </a>
            
            <a href="{redirect_uri}?code=mock_google_123&provider=google" class="btn">Tiếp tục với tài khoản Mock</a>
            <a href="http://127.0.0.1:3000/login" class="cancel-link">Hủy bỏ</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.post("/google/callback", response_model=Token)
async def google_callback(data: CallbackRequest):
    """
    Callback endpoint to exchange authorization code for JWT token.
    Supports both real and mock auth codes.
    """
    code = data.code
    
    if code.startswith("mock_"):
        email = "mock.google.user@gmail.com"
        username = "mock_google_user"
    else:
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google OAuth is not configured on this server."
            )
            
        async with httpx.AsyncClient() as client:
            # 1. Exchange code for tokens
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )
            if token_resp.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code: {token_resp.text}"
                )
                
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            
            # 2. Get user info
            userinfo_resp = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if userinfo_resp.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to retrieve user info: {userinfo_resp.text}"
                )
                
            user_info = userinfo_resp.json()
            email = user_info.get("email")
            name = user_info.get("name") or user_info.get("given_name") or "google_user"
            username = email.split("@")[0] if email else name.lower().replace(" ", "_")
            
    username_clean = username.strip()
    
    # Check if user already exists
    rows = await execute_query("SELECT id, username, email FROM users WHERE email = ? OR username = ?", [email, username_clean])
    
    if not rows:
        # Create user
        from server.auth import get_password_hash
        dummy_pwd = get_password_hash(str(uuid.uuid4()))
        created_at = datetime.now().isoformat(timespec="seconds")
        
        await execute_query(
            "INSERT INTO users (username, hashed_password, email, created_at) VALUES (?, ?, ?, ?)",
            [username_clean, dummy_pwd, email, created_at]
        )
        
        rows = await execute_query("SELECT username FROM users WHERE email = ?", [email])
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register user record in database"
            )
            
    user_record = rows[0]
    jwt_token = create_access_token(data={"sub": user_record["username"]})
    return Token(access_token=jwt_token, token_type="bearer")
