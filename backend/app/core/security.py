from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext

from supabase import create_client, Client
from app.core.config import settings

# Password hashing context using bcrypt algo
_pwd_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize Supabase client
supabase: Client = create_client(
    str(settings.supabase_url), 
    settings.supabase_service_role_key.get_secret_value()
)

def get_password_hash(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        password: The plain-text password to hash.

    Returns:
        The hashed password string.
    """
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hashed password.

    Args:
        plain_password: The candidate plain-text password.
        hashed_password: The stored hashed password.

    Returns:
        True if the password matches, False otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# JWT configuration: prefer explicit settings on the centralized Settings object,
# fall back to sensible defaults when strictly necessary.
_JWT_SECRET_KEY: str = (
    settings.supabase_jwt_secret.get_secret_value()
    if getattr(settings, "supabase_jwt_secret", None)
    else (
        settings.supabase_service_role_key.get_secret_value()
        if getattr(settings, "supabase_service_role_key", None)
        else ""
    )
)
_JWT_ALGORITHM: list[str] = ["ES256", "HS256"]
_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(getattr(settings, "access_token_expire_minutes", 60))


class TokenError(Exception):
    pass


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Create a signed JWT access token for the given subject.

    Args:
        subject: The principal subject (commonly a user id or uuid) to embed in the token's "sub" claim.
        expires_delta: Optional custom expiry delta. If omitted, defaults to configured ACCESS_TOKEN_EXPIRE_MINUTES.
        extra_claims: Optional additional claims to include in the token payload.

    Returns:
        A signed JWT as a string.
    """
    if not _JWT_SECRET_KEY:
        raise TokenError("JWT secret key is not configured; cannot create tokens")

    now = datetime.utcnow()
    expire = now + (expires_delta if expires_delta is not None else timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES))

    payload: Dict[str, Any] = {"sub": str(subject), "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    if extra_claims:
        payload.update(extra_claims)

    token: str = jwt.encode(payload, _JWT_SECRET_KEY, algorithm=_JWT_ALGORITHM)
    # PyJWT may return bytes on some older versions; ensure string
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


# def decode_token(token: str) -> Dict[str, Any]:
#     """Decode and validate a JWT, returning the payload.

#     Raises TokenError on validation failures.

#     Args:
#         token: The JWT string to decode.

#     Returns:
#         The decoded payload as a dict.
#     """
#     if not _JWT_SECRET_KEY:
#         raise TokenError("JWT secret key is not configured; cannot decode tokens")

#     try:
#         payload = jwt.decode(token, _JWT_SECRET_KEY, algorithms=_JWT_ALGORITHM, options={"verify_aud": False})
#     except jwt.ExpiredSignatureError as exc:
#         raise TokenError("Token has expired") from exc
#     except jwt.InvalidTokenError as exc:
#         raise TokenError(f"Invalid token: {exc}") from exc

#     return payload


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT using Supabase Auth."""
    try:
        # Ask Supabase Auth to verify the JWT token
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        
        if not user:
            raise TokenError("User not found or token invalid")

        # Map user claims into payload dict expected by application
        return {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "user_metadata": user.user_metadata,
        }
    except Exception as exc:
        raise TokenError(f"Invalid token: {exc}") from exc


def get_token_subject(token: str) -> str:
    """Extract the "sub" (subject) claim from a validated token.

    Raises TokenError if token is invalid or subject is missing.
    """
    payload = decode_token(token)
    subject = payload.get("sub")
    if subject is None:
        raise TokenError("Token payload missing 'sub' claim")
    return str(subject)


__all__ = [
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "decode_token",
    "get_token_subject",
    "TokenError",
]
