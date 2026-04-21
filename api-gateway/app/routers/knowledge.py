from fastapi import APIRouter, Depends

from app.auth import require_current_user
from app.context import build_core_headers
from app.core_client import forward
from app.models import KnowledgeSourceCreateRequest, KnowledgeSourcePatchRequest
from app.schemas import ApiResponse

router = APIRouter(
    prefix="/api/v1/tm",
    tags=["knowledge"],
    dependencies=[Depends(require_current_user)],
)


@router.post("/knowledge-sources", response_model=ApiResponse)
async def create_knowledge_source(
    payload: KnowledgeSourceCreateRequest, claims: dict = Depends(require_current_user)
) -> dict:
    return await forward(
        "POST",
        "/internal/core/knowledge/sources",
        json_body=payload.model_dump(),
        headers=build_core_headers(claims),
    )


@router.get("/knowledge-sources", response_model=ApiResponse)
async def list_knowledge_sources(claims: dict = Depends(require_current_user)) -> dict:
    return await forward(
        "GET", "/internal/core/knowledge/sources", headers=build_core_headers(claims)
    )


@router.get("/knowledge-sources/{source_id}", response_model=ApiResponse)
async def get_knowledge_source(source_id: str, claims: dict = Depends(require_current_user)) -> dict:
    return await forward(
        "GET",
        f"/internal/core/knowledge/sources/{source_id}",
        headers=build_core_headers(claims),
    )


@router.post("/knowledge-sources/{source_id}/sync", response_model=ApiResponse)
async def sync_knowledge_source(source_id: str, claims: dict = Depends(require_current_user)) -> dict:
    return await forward(
        "POST",
        f"/internal/core/knowledge/sources/{source_id}/sync",
        headers=build_core_headers(claims),
    )


@router.patch("/knowledge-sources/{source_id}", response_model=ApiResponse)
async def patch_knowledge_source(
    source_id: str,
    payload: KnowledgeSourcePatchRequest,
    claims: dict = Depends(require_current_user),
) -> dict:
    return await forward(
        "PATCH",
        f"/internal/core/knowledge/sources/{source_id}",
        json_body=payload.model_dump(exclude_none=True),
        headers=build_core_headers(claims),
    )


@router.delete("/knowledge-sources/{source_id}", response_model=ApiResponse)
async def delete_knowledge_source(source_id: str, claims: dict = Depends(require_current_user)) -> dict:
    return await forward(
        "DELETE",
        f"/internal/core/knowledge/sources/{source_id}",
        headers=build_core_headers(claims),
    )


@router.get("/knowledge-chunks", response_model=ApiResponse)
async def list_knowledge_chunks(
    source_id: str | None = None,
    keyword: str | None = None,
    claims: dict = Depends(require_current_user),
) -> dict:
    return await forward(
        "GET",
        "/internal/core/knowledge/chunks",
        params={"source_id": source_id, "keyword": keyword},
        headers=build_core_headers(claims),
    )
