from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()
security = HTTPBearer()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    """ログイン"""
    try:
        user = await auth_service.authenticate_user(
            login_request.username, login_request.password
        )
        print(f"[login] authenticate_user result: {user}")
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not isinstance(user, dict) or "username" not in user:
            print(f"[login] user object missing 'username': {user}")
            raise HTTPException(
                status_code=500, detail="User object missing 'username' field"
            )
        access_token = auth_service.create_access_token(data={"sub": user["username"]})
        return LoginResponse(access_token=access_token, expires_in=3600)  # 1時間
    except HTTPException as he:
        print(f"[login] HTTPException: {he.detail}")
        raise
    except Exception as e:
        print(f"[login] Unexpected error during login: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during authentication"
        )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """ログアウト"""
    # JWTトークンは無効化できないため、クライアント側で破棄する
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_info(user=Depends(auth_service.get_current_user)):
    """現在のユーザー情報を取得"""
    return {"username": user["username"], "role": user.get("role", "user")}
