from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

# 設定
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# パスワードハッシュ化
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ダミーユーザーデータベース（本番環境では実際のDBを使用）
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123"),
        "role": "admin"
    },
    "user": {
        "username": "user", 
        "hashed_password": pwd_context.hash("user123"),
        "role": "user"
    }
}

class AuthService:
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """パスワードを検証"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            print(f"Error verifying password: {e}")
            return False
    
    def get_password_hash(self, password: str) -> str:
        """パスワードをハッシュ化"""
        try:
            return pwd_context.hash(password)
        except Exception as e:
            print(f"Error hashing password: {e}")
            raise
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """ユーザー認証"""
        try:
            user = fake_users_db.get(username)
            if not user:
                return None
            if not self.verify_password(password, user["hashed_password"]):
                return None
            return user
        except Exception as e:
            print(f"Error during user authentication: {e}")
            return None
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """アクセストークンを作成"""
        try:
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt
        except Exception as e:
            print(f"Error creating access token: {e}")
            raise
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """現在のユーザーを取得"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError as e:
            print(f"JWT decode error: {e}")
            raise credentials_exception
        except Exception as e:
            print(f"Unexpected error in get_current_user: {e}")
            raise credentials_exception
        
        user = fake_users_db.get(username)
        if user is None:
            raise credentials_exception
        return user

# 依存性注入用のインスタンス
auth_service = AuthService()

# グローバル関数として公開
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    return await auth_service.get_current_user(credentials)