from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session
from backend.app.schemas.jobs import IngestionJobStatusResponse
from backend.app.services.ingestion import (
    IngestionJobNotFoundError,
    get_ingestion_job_status,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=IngestionJobStatusResponse)
def get_job(job_id: int, db: Session = Depends(get_db_session)):
    try:
        return get_ingestion_job_status(db=db, job_id=job_id)
    except IngestionJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        ) from exc
