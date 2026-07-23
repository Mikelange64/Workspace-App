import json
from datetime import datetime, UTC
from typing import Literal

import httpx
from fastapi import HTTPException, status
from openai import OpenAI

from app.config import settings
from app.database import DbSession
from app.models import ConversationType, Message, SenderType
from app.schemas import MessageResponse
from app.utils import get_conversation_by_id_with_messages, get_workspace_task_index


MODEL = "deepseek-v4-flash"
API_KEY = settings.deepseek_api_key.get_secret_value()

# Bounds how many search -> re-ask round trips a single reply() call can make,
# so a confused model can't loop indefinitely (and rack up search charges).
MAX_SEARCH_ROUNDS = 3

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information not in your training data - "
            "news, prices, recent events, or anything time-sensitive."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        },
    },
}

# Only advertise the search tool - and claim the capability in the system
# prompt - when a Tavily key is actually configured. Otherwise the bot would
# either try to call a tool that has no key to run with, or falsely claim it
# can look things up.
if settings.tavily_api_key:
    _SEARCH_CAPABILITY_LINE = (
        "You have access to a web search tool. Use it when a question needs "
        "current information or something outside your own knowledge — don't "
        "guess when you can look it up."
    )
else:
    _SEARCH_CAPABILITY_LINE = (
        "You do not have access to web search or the ability to read URLs - "
        "answer from your own knowledge, and say so plainly if a question needs "
        "current information you don't have rather than guessing."
    )

BASE_SYSTEM_PROMPT = (
    "You are Filobelo, an assistant embedded in a workspace collaboration tool. "
    "You are read-only: you cannot create, edit, or delete anything.\n\n"
    f"{_SEARCH_CAPABILITY_LINE}\n\n"
    "Be direct and objective — don't flatter, don't soften disagreement, don't tell "
    "people what they want to hear. If you're not sure about something, say so "
    "plainly instead of guessing or filling gaps with plausible-sounding content.\n\n"
    "Keep replies conversational and to the point — this is a chat interface, not a "
    "document."
)
_TURN_ROLE : dict[SenderType, Literal["user", "assistant"]] = {
    SenderType.USER: "user",
    SenderType.BOT: "assistant",
}


class FilobeloBot:
    def __init__(self):
        self.client = OpenAI(
            api_key=API_KEY,
            base_url="https://api.deepseek.com"
        )

    def reply(
        self,
        conversation_id : int,
        workspace_id    : int,
        db              : DbSession,
    ) -> MessageResponse:
        conversation = get_conversation_by_id_with_messages(
            conversation_id, workspace_id, db
        )

        if conversation.type != ConversationType.BOT:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND, detail = "Conversation not found"
            )

        history = self._build_history(conversation.messages)
        system_prompt = self._build_system_prompt(workspace_id, db)
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
        ]

        try:
            message, sources = self._run_completion(messages)
        except Exception as e :
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service unavailable"
            ) from e

        reply = message.content
        if not reply:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service unavailable"
            )

        now = datetime.now(UTC)
        new_message = Message(
            conversation_id = conversation_id,
            sender_type     = SenderType.BOT,
            content         = reply,
            sources         = sources or None,
            created_at      = now
        )
        conversation.last_message_at = now

        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        response = MessageResponse.model_validate(new_message)
        return response


    def _run_completion(self, messages: list[dict]) -> tuple[object, list[dict]]:
        """Calls the model, and if it requests the web_search tool, runs the
        search and feeds the result back - up to MAX_SEARCH_ROUNDS times -
        before returning the final assistant message, plus every source
        (deduped by url) collected along the way."""
        tools = [SEARCH_TOOL] if settings.tavily_api_key else None
        sources: list[dict] = []
        seen_urls: set[str] = set()

        for _ in range(MAX_SEARCH_ROUNDS):
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                stream=False,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}}
            )
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                return message, sources

            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            })
            for call in tool_calls:
                args = json.loads(call.function.arguments)
                result, results = self._search_web(args.get("query", ""))
                for r in results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        sources.append(r)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result,
                })

        # Ran out of search rounds - ask once more without tools so the model
        # is forced to answer with whatever it has instead of looping again.
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=False,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}}
        )
        return response.choices[0].message, sources


    @staticmethod
    def _search_web(query: str, max_results: int = 5) -> tuple[str, list[dict]]:
        if not settings.tavily_api_key:
            return "Web search is not available right now.", []

        try:
            response = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key.get_secret_value(),
                    "query": query,
                    "max_results": max_results,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        except Exception as e:
            return f"Search failed: {e}", []

        if not results:
            return "No results found.", []

        formatted = "\n".join(
            f"- {r.get('title', '')} ({r.get('url', '')}): {r.get('content', '')[:300]}"
            for r in results
        )
        sources = [
            {"title": r.get("title") or r.get("url", ""), "url": r["url"]}
            for r in results
            if r.get("url")
        ]
        return formatted, sources


    @staticmethod
    def _build_history(messages: list[Message]) -> list:
        return [
            {"role": _TURN_ROLE[m.sender_type], "content": m.content}
            for m in messages
        ]


    @staticmethod
    def _build_system_prompt(workspace_id: int, db: DbSession) -> str:
        tasks = get_workspace_task_index(workspace_id, db)

        if not tasks:
            return BASE_SYSTEM_PROMPT + "\n\nThis workspace currently has no tasks."

        lines = ["Here is an index of this workspace's tasks and resources:"]
        for task in tasks:
            lines.append(f'- Task #{task.id} "{task.title}"')
            for resource in task.resources:
                lines.append(
                    f'    - {resource.type.value} #{resource.id} "{resource.title}"'
                )

        return BASE_SYSTEM_PROMPT + "\n\n" + "\n".join(lines)


filobelo_bot = FilobeloBot()
