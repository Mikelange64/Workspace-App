from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.database import DbSession
from app.dependencies import require_membership
from app.models import Conversation, ConversationType, Message, WorkspaceMember
from app.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
    PaginatedMessageResponse,
)
from app.utils import get_conversation_by_id


router = APIRouter(prefix="/{workspace_id}/conversations", tags=["conversations"])


def _require_creator_or_admin(conversation: Conversation, member: WorkspaceMember) -> None:
    if conversation.creator_id != member.user_id and member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the conversation creator or an admin can perform this action",
        )


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    workspace_id: int,
    data: ConversationCreate,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    new_conversation = Conversation(
        workspace_id = workspace_id,
        creator_id   = member.user_id,
        type         = ConversationType.WORKSPACE,
        title        = data.title,
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    return new_conversation


@router.get(
    "/", response_model=list[ConversationResponse], dependencies=[Depends(require_membership)]
)
def list_conversations(workspace_id: int, db: DbSession):
    return db.execute(
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.is_pinned.desc(), Conversation.created_at.desc())
    ).scalars().all()


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    dependencies=[Depends(require_membership)],
)
def get_conversation(conversation_id: int, workspace_id: int, db: DbSession):
    return get_conversation_by_id(conversation_id, workspace_id, db)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id : int,
    workspace_id    : int,
    data            : ConversationUpdate,
    db              : DbSession,
    member          : Annotated[WorkspaceMember, Depends(require_membership)],
):
    conversation = get_conversation_by_id(conversation_id, workspace_id, db)
    _require_creator_or_admin(conversation, member)

    update = data.model_dump(exclude_unset=True)
    for field, value in update.items():
        setattr(conversation, field, value)

    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    workspace_id: int,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    conversation = get_conversation_by_id(conversation_id, workspace_id, db)
    _require_creator_or_admin(conversation, member)

    db.delete(conversation)
    db.commit()


# =============================================== MESSAGES ===================================================

@router.post(
    "/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED
)
def send_message(
    conversation_id: int,
    workspace_id: int,
    data: MessageCreate,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    get_conversation_by_id(conversation_id, workspace_id, db)

    new_message = Message(
        conversation_id = conversation_id,
        sender_id       = member.user_id,
        content         = data.content,
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


@router.get(
    "/{conversation_id}/messages",
    response_model=PaginatedMessageResponse,
    dependencies=[Depends(require_membership)],
)
def list_messages(
    conversation_id: int,
    workspace_id: int,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
):
    get_conversation_by_id(conversation_id, workspace_id, db)

    base = select(Message).where(Message.conversation_id == conversation_id)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar() or 0
    messages = (
        db.execute(base.order_by(Message.created_at).offset(skip).limit(limit))
        .scalars().all()
    )

    return PaginatedMessageResponse(
        messages=messages,
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + limit < total,
    )


@router.delete("/{conversation_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    conversation_id: int,
    workspace_id: int,
    message_id: int,
    db: DbSession,
    member: Annotated[WorkspaceMember, Depends(require_membership)],
):
    get_conversation_by_id(conversation_id, workspace_id, db)

    message = db.execute(
        select(Message).where(Message.id == message_id, Message.conversation_id == conversation_id)
    ).scalars().first()

    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if message.sender_id != member.user_id and member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender or an admin can delete this message",
        )

    db.delete(message)
    db.commit()
