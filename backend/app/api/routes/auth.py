from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session
from backend.app.schemas.auth import AuthLoginRequest, AuthRegisterRequest, AuthTokenResponse
from backend.app.services.auth_service import (
    AuthConflictError,
    AuthenticationError,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: AuthRegisterRequest,
    response: Response,
    db: Session = Depends(get_db_session),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return register_user(db=db, payload=payload)
    except AuthConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant name or email already exists.",
        ) from exc


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: AuthLoginRequest,
    response: Response,
    db: Session = Depends(get_db_session),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return authenticate_user(db=db, payload=payload)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
