from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class ConversationCreate(BaseModel):
    title : str = Field(min_length=1, max_length=100)


class ConversationUpdate(BaseModel):
    title       : str | None = Field(default=None, min_length=1, max_length=100)
    is_pinned   : bool | None = None
    is_archived : bool | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id              : int
    workspace_id    : int
    creator_id      : int | None
    title           : str
    created_at      : datetime
    is_pinned       : bool
    is_archived     : bool
    last_message_at : datetime | None = None


class MessageCreate(BaseModel):
    content : str = Field(min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id              : int
    conversation_id : int
    sender_id       : int | None
    content         : str
    created_at      : datetime


class PaginatedMessageResponse(BaseModel):
    messages : list[MessageResponse]
    total    : int
    skip     : int
    limit    : int
    has_more : bool
