from typing import Any

from pydantic import BaseModel


class KnowledgeSourceCreatePayload(BaseModel):
    type: str
    name: str
    config: dict[str, Any]
    tags: list[str] = []


class KnowledgeSourcePatchPayload(BaseModel):
    name: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class ChatSessionCreatePayload(BaseModel):
    channel: str
    visitor_id: str
    metadata: dict[str, Any] | None = None


class ChatMessagePayload(BaseModel):
    role: str = "user"
    content: str


class HandoffPayload(BaseModel):
    reason: str


class HandoffReplyPayload(BaseModel):
    content: str
    mark_as_kb_candidate: bool = False


class CandidateRejectPayload(BaseModel):
    reason: str | None = None


class RetrievalDebugPayload(BaseModel):
    query: str
    top_k: int = 5
