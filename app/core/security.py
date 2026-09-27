import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from config import config


password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

class TokenError(Exception):
    pass


def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: str,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }

    return jwt.encode(
        payload,
        config.jwt_secret_key,
        algorithm=config.jwt_algorithm,
    )


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(
        subject=str(user_id),
        expires_delta=timedelta(
            minutes=config.access_token_expire_minutes
        ),
        token_type="access",
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        subject=str(user_id),
        expires_delta=timedelta(
            days=config.refresh_token_expire_days
        ),
        token_type="refresh",
    )


def decode_token(
    token: str,
    expected_type: str,
) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret_key,
            algorithms=[config.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise TokenError("Token expired")
    except jwt.InvalidTokenError:
        raise TokenError("Invalid token")

    if payload.get("type") != expected_type:
        raise TokenError(f"Expected {expected_type} token")

    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise TokenError("Invalid token subject")