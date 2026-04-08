from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.session import get_db_session
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    TenantResponse,
    UserResponse,
)

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)
PASSWORD_HASH_ITERATIONS = 200_000


class AuthenticationError(Exception):
    """Raised when credentials are invalid."""


class AuthConflictError(Exception):
    """Raised when auth registration conflicts with existing records."""


def register_user(db: Session, payload: AuthRegisterRequest) -> AuthTokenResponse:
    tenant = Tenant(name=payload.tenant_name)
    user = User(
        tenant=tenant,
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add_all([tenant, user])
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthConflictError from exc
    db.refresh(tenant)
    db.refresh(user)
    return _build_token_response(user)


def authenticate_user(db: Session, payload: AuthLoginRequest) -> AuthTokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError
    if not user.is_active:
        raise AuthenticationError
    return _build_token_response(user)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized_error()

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.auth_secret_key,
            algorithms=[settings.auth_jwt_algorithm],
        )
        user_id = int(payload.get("sub"))
        tenant_id = int(payload.get("tenant_id"))
    except Exception as exc:
        raise _unauthorized_error() from exc

    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .where(User.tenant_id == tenant_id)
        .where(User.is_active.is_(True))
    )
    if user is None:
        raise _unauthorized_error()
    return user


def create_access_token(user: User) -> tuple[str, int]:
    expires_delta = timedelta(minutes=settings.auth_access_token_expire_minutes)
    expires_at = datetime.now(UTC) + expires_delta
    encoded = jwt.encode(
        {
            "sub": str(user.id),
            "tenant_id": user.tenant_id,
            "exp": expires_at,
        },
        settings.auth_secret_key,
        algorithm=settings.auth_jwt_algorithm,
    )
    return encoded, int(expires_delta.total_seconds())


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return "$".join(
        [
            "pbkdf2_sha256",
            str(PASSWORD_HASH_ITERATIONS),
            urlsafe_b64encode(salt).decode("utf-8"),
            urlsafe_b64encode(digest).decode("utf-8"),
        ]
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iteration_count, encoded_salt, encoded_digest = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = urlsafe_b64decode(encoded_salt.encode("utf-8"))
        expected_digest = urlsafe_b64decode(encoded_digest.encode("utf-8"))
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iteration_count),
        )
    except Exception:
        return False
    return hmac.compare_digest(actual_digest, expected_digest)


def _build_token_response(user: User) -> AuthTokenResponse:
    access_token, expires_in_seconds = create_access_token(user)
    tenant = user.tenant
    return AuthTokenResponse(
        access_token=access_token,
        expires_in_seconds=expires_in_seconds,
        user=UserResponse.model_validate(user),
        tenant=TenantResponse.model_validate(tenant),
    )


def _unauthorized_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
