import asyncio
import json
import uuid

from langfuse import get_client, Langfuse
from langfuse.langchain import CallbackHandler
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_graph, get_llm
from app.db.database import AsyncSessionLocal
from app.db.models import Conversation, Message, User
from app.schemas.conversation import ConversationSummary, ConversationDetail, SendMessageRequest
from memory.long_term import LongTermMemory
from config import config


router = APIRouter()

NODE_STATUS_MESSAGES = {
    "Supervisor": "Thinking...",
    "Flight": "Searching flights...",
    "Hotel": "Searching hotels...",
    "Planner": "Putting together your itinerary...",
}

TITLE_PROMPT = (
    "Summarize this message as a short conversation title, 4 words max, "
    "no quotes, no trailing punctuation:\n\n{message}"
)

Langfuse(
    public_key=config.langfuse_public_key,
    secret_key=config.langfuse_secret_key,
    base_url=config.langfuse_base_url
)

langfuse = get_client()
langfuse_handler = CallbackHandler()


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(conversation_id, user, db)

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "messages": messages,
    }


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _get_owned_conversation(conversation_id, user, db)
    await db.delete(conversation)
    await db.commit()


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    graph=Depends(get_graph),
    llm=Depends(get_llm),
):
    conversation = await _get_owned_conversation(conversation_id, user, db)
    conv_id = conversation.id
    user_id = user.id

    result = await db.execute(
        select(Message.id).where(Message.conversation_id == conv_id).limit(1)
    )
    is_new_conversation = result.scalar_one_or_none() is None

    db.add(Message(conversation_id=conv_id, role="user", content=payload.content))
    await db.commit()

    return StreamingResponse(
        _stream_turn(conv_id, user_id, payload.content, is_new_conversation, graph, llm),
        media_type="text/event-stream",
    )

async def _get_owned_conversation(conversation_id: uuid.UUID, user: User, db: AsyncSession) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


def _sse(event_type: str, data: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


async def _stream_turn(conversation_id, user_id, user_text, is_new_conversation, graph, llm):
    thread_id = str(conversation_id)
    run_config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [langfuse_handler],
        "run_name": "travel-agent",
        "metadata": {
            "langfuse_session_id": thread_id,
            "langfuse_user_id": str(user_id),
        },
    }

    async with AsyncSessionLocal() as db:
        if is_new_conversation:
            title = await _generate_title(llm, user_text)
            conversation = await db.get(Conversation, conversation_id)
            conversation.title = title
            await db.commit()
            yield _sse("title", {"title": title})

        long_term_memory = LongTermMemory(session=db, llm=llm)
        preferences = await long_term_memory.get(user_id, query=user_text)

        initial_state = {
            "messages": [{"role": "user", "content": user_text}],
            "user_preferences": preferences,
        }

        streamed_tokens = False
        seen_nodes = set()
        final_response = ""

        try:
            async for event in graph.astream_events(initial_state, config=run_config, version="v2"):
                kind = event["event"]
                node_name = event.get("metadata", {}).get("langgraph_node")

                if kind == "on_chain_start" and node_name in NODE_STATUS_MESSAGES and node_name not in seen_nodes:
                    seen_nodes.add(node_name)
                    yield _sse("status", {"node": node_name, "message": NODE_STATUS_MESSAGES[node_name]})

                elif kind == "on_chat_model_stream" and node_name == "Planner":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        streamed_tokens = True
                        yield _sse("token", {"content": chunk.content})

            snapshot = await graph.aget_state(run_config)
            final_response = snapshot.values["messages"][-1].content

            if not streamed_tokens and final_response:
                yield _sse("token", {"content": final_response})

        except Exception as exc:
            yield _sse("error", {"message": str(exc)})
            return

        assistant_message = Message(
            conversation_id=conversation_id, role="assistant", content=final_response
        )
        db.add(assistant_message)
        await db.commit()

        yield _sse("done", {"message_id": str(assistant_message.id)})

    asyncio.create_task(_extract_memory_background(user_id, user_text, final_response, llm))


async def _extract_memory_background(user_id: uuid.UUID, user_text: str, final_response: str, llm):
    async with AsyncSessionLocal() as session:
        try:
            await LongTermMemory(session=session, llm=llm).extract_and_store(
                user_id=user_id,
                user_message=user_text,
                assistant_response=final_response,
            )
        except Exception:
            pass  


async def _generate_title(llm, first_message: str) -> str:
    response = await llm.ainvoke(TITLE_PROMPT.format(message=first_message))
    return response.content.strip().strip('"')