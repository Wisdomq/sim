"""Branch and brand-ambassador account routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from simcards_backend.api.dependencies import get_current_user, require_hq, require_hq_or_branch
from simcards_backend.core.database import get_db
from simcards_backend.models import Role, User
from simcards_backend.schemas.accounts import (
    BranchCreateRequest,
    BranchResponse,
    BrandAmbassadorCreateRequest,
    BrandAmbassadorResponse,
    PhotoUploadResponse,
)
from simcards_backend.services.accounts import (
    create_branch_account,
    create_brand_ambassador_account,
    list_branches,
    list_brand_ambassadors,
    remove_branch_account,
    remove_brand_ambassador_account,
    resolve_photo,
    save_uploaded_photo,
)

router = APIRouter(tags=["accounts"])


@router.post(
    "/branches",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_branch(
    payload: BranchCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    return create_branch_account(
        db,
        actor=current_user,
        name=payload.name,
        branch_type=payload.type,
        id_number=payload.id_number,
        photo_url=payload.photo_url,
        email=payload.email,
        password=payload.password,
    )


@router.get("/branches", response_model=list[BranchResponse])
def get_branches(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    return list_branches(db, actor=current_user)


@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    remove_branch_account(db, actor=current_user, branch_id=branch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/branches/{branch_id}/brand-ambassadors",
    response_model=BrandAmbassadorResponse,
    status_code=status.HTTP_201_CREATED,
)
def hq_create_brand_ambassador(
    branch_id: int,
    payload: BrandAmbassadorCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    return create_brand_ambassador_account(
        db,
        actor=current_user,
        branch_id=branch_id,
        name=payload.name,
        email=payload.email,
        password=payload.password,
        phone_msisdn=payload.phone_msisdn,
        id_number=payload.id_number,
        photo_url=payload.photo_url,
    )


@router.post(
    "/brand-ambassadors",
    response_model=BrandAmbassadorResponse,
    status_code=status.HTTP_201_CREATED,
)
def branch_create_brand_ambassador(
    payload: BrandAmbassadorCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    branch_id = current_user.branch_id if current_user.role == Role.BRANCH else None
    if branch_id is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HQ users must create BAs through /branches/{branch_id}/brand-ambassadors.",
        )
    return create_brand_ambassador_account(
        db,
        actor=current_user,
        branch_id=branch_id,
        name=payload.name,
        email=payload.email,
        password=payload.password,
        phone_msisdn=payload.phone_msisdn,
        id_number=payload.id_number,
        photo_url=payload.photo_url,
    )


@router.get("/brand-ambassadors", response_model=list[BrandAmbassadorResponse])
def get_brand_ambassadors(
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    return list_brand_ambassadors(db, actor=current_user, branch_id=branch_id)


@router.get("/brand-ambassadors/{ba_id}", response_model=BrandAmbassadorResponse)
def get_brand_ambassador(
    ba_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq_or_branch),
):
    from simcards_backend.services.accounts import get_brand_ambassador as _get_ba

    return _get_ba(db, actor=current_user, ba_id=ba_id)


@router.delete("/brand-ambassadors/{ba_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand_ambassador(
    ba_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hq),
):
    remove_brand_ambassador_account(db, actor=current_user, ba_id=ba_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/uploads/photo",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a Branch/BA identity photo; returns the authorized photo URL."""
    photo_url, file_reference = save_uploaded_photo(actor=current_user, file=file)
    return PhotoUploadResponse(photo_url=photo_url, file_reference=file_reference)


@router.get("/uploads/photo/{filename}")
def get_uploaded_photo(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Serve an uploaded photo, scoped to the caller's dealer."""
    path = resolve_photo(dealer_id=current_user.dealer_id, filename=filename)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    return FileResponse(path)
