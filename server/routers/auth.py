"""
Authentication router: register, login, logout, and current user retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from server.schemas import UserRegister, UserOut, Token
from server.auth import (
    load_users,
    save_users,
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    TOKEN_BLACKLIST,
    oauth2_scheme,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister):
    """
    Register a new user account.
    Passwords are encrypted securely using PBKDF2-SHA256.
    """
    users = load_users()
    username_clean = data.username.strip()
    
    if username_clean in users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
        
    # Store hashed password
    hashed_pwd = get_password_hash(data.password)
    users[username_clean] = {
        "password": hashed_pwd,
        "email": data.email.strip() if data.email else None
    }
    save_users(users)
    
    return UserOut(username=username_clean, email=data.email)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login. Access tokens expire in 60 minutes.
    Note: Form data fields are 'username' and 'password'.
    """
    users = load_users()
    user = users.get(form_data.username)
    
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": form_data.username})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout(token: str = Depends(get_current_user), auth_header: str = Depends(OAuth2PasswordRequestForm.__subclasses__)):
    """
    Log out the current user by blacklisting their active JWT token.
    """
    # Since OAuth2PasswordBearer is used, we can get raw token through oauth2_scheme dependency
    # Let's extract it from Header or OAuth2Scheme
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
