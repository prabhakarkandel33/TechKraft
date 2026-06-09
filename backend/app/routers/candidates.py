from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional

from app.models import get_db
from app.schemas import (
    ScoreRequest,
    ScoreResponse,
    CandidateListResponse,
    CandidateDetailResponse,
    SummaryResponse,
    InternalNotesRequest,
)
from app.auth import get_current_user, get_current_admin, TokenData
from app.services.candidate_service import (
    list_candidates,
    get_candidate_detail,
    create_score,
    generate_summary,
    update_internal_notes,
    soft_delete_candidate,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListResponse, response_model_exclude_none=True)
async def get_candidates(
    status: Optional[str] = Query(None),
    role_applied: Optional[str] = Query(None),
    skill: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    is_admin = current_user.role == "admin"

    result = await list_candidates(
        db=db,
        status=status,
        role_applied=role_applied,
        skill=skill,
        keyword=keyword,
        page=page,
        page_size=page_size,
        is_admin=is_admin,
    )
    return result


@router.get("/{candidate_id}", response_model=CandidateDetailResponse, response_model_exclude_none=True)
async def get_candidate(
    candidate_id: str,
    db=Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    is_admin = current_user.role == "admin"

    candidate = await get_candidate_detail(
        db=db,
        candidate_id=candidate_id,
        current_user_id=current_user.user_id,
        is_admin=is_admin,
    )

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="candidate not found",
        )

    return candidate


@router.post("/{candidate_id}/scores", response_model=ScoreResponse, status_code=201)
async def submit_score(
    candidate_id: str,
    body: ScoreRequest,
    db=Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    result = await create_score(
        db=db,
        candidate_id=candidate_id,
        category=body.category,
        score=body.score,
        reviewer_id=current_user.user_id,
        note=body.note,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="candidate not found",
        )

    return result


@router.post("/{candidate_id}/summary", response_model=SummaryResponse)
async def trigger_summary(
    candidate_id: str,
    db=Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    # this awaits a 2s mock delay — in prod this would be
    # an actual await to Bedrock, same pattern
    result = await generate_summary(db=db, candidate_id=candidate_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="candidate not found",
        )

    return result


@router.patch("/{candidate_id}/notes", status_code=200)
async def edit_internal_notes(
    candidate_id: str,
    body: InternalNotesRequest,
    db=Depends(get_db),
    current_user: TokenData = Depends(get_current_admin),  # admin only
):
    result = await update_internal_notes(
        db=db,
        candidate_id=candidate_id,
        notes=body.internal_notes,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="candidate not found",
        )

    return result


@router.delete("/{candidate_id}", status_code=204)
async def delete_candidate(
    candidate_id: str,
    db=Depends(get_db),
    current_user: TokenData = Depends(get_current_admin),  # admin only
):
    deleted = await soft_delete_candidate(db=db, candidate_id=candidate_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="candidate not found",
        )