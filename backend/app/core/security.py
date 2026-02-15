"""
安全工具模块
提供密码哈希、JWT生成和验证等功能
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 密码上下文（使用bcrypt）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        bool: 密码是否正确
    """
    # bcrypt has a maximum password length of 72 bytes
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    哈希密码

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    # bcrypt限制密码不能超过72字节
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建访问令牌（JWT）

    Args:
        data: 要编码的数据（通常包含user_id, email, role等）
        expires_delta: 过期时间增量，默认15分钟

    Returns:
        str: JWT令牌字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建刷新令牌

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量，默认7天

    Returns:
        str: 刷新令牌字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码JWT令牌

    Args:
        token: JWT令牌字符串

    Returns:
        Dict[str, Any] | None: 解码后的数据，失败返回None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    验证JWT令牌并检查类型

    Args:
        token: JWT令牌字符串
        token_type: 令牌类型，"access" 或 "refresh"

    Returns:
        Dict[str, Any] | None: 验证成功返回payload，失败返回None
    """
    payload = decode_token(token)

    if payload is None:
        return None

    # 检查令牌类型
    if payload.get("type") != token_type:
        return None

    # 检查是否过期
    exp = payload.get("exp")
    if exp is None:
        return None

    if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        return None

    return payload


def create_token_pair(user_data: Dict[str, Any]) -> Dict[str, str]:
    """
    创建访问令牌和刷新令牌对

    Args:
        user_data: 用户数据（包含user_id, email, role等）

    Returns:
        Dict[str, str]: 包含access_token和refresh_token的字典
    """
    access_token = create_access_token(data=user_data)
    refresh_token = create_refresh_token(data={"sub": user_data.get("sub")})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
