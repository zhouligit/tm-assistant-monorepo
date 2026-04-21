from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class KnowledgeSourceCreateRequest(BaseModel):
    type: str = Field(description="feishu_doc/web_url/pdf/faq")
    name: str
    config: dict[str, Any]
    tags: list[str] = []


class KnowledgeSourcePatchRequest(BaseModel):
    name: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class ChatSessionCreateRequest(BaseModel):
    channel: str
    visitor_id: str
    metadata: dict[str, Any] | None = None


class ChatMessageRequest(BaseModel):
    role: str = "user"
    content: str


class ChatHandoffRequest(BaseModel):
    reason: str


class HandoffReplyRequest(BaseModel):
    content: str
    mark_as_kb_candidate: bool = False


class CandidateRejectRequest(BaseModel):
    reason: str | None = None


class RetrievalDebugRequest(BaseModel):
    query: str
    top_k: int = 5
