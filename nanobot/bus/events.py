from dataclasses import dataclass, field
from typing import Any


@dataclass
class InboundMessage:
    channel: str
    sender_id: str
    chat_id: str
    content: str
    media: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    session_key_override: str | None = None


@dataclass
class OutboundMessage:
    channel: str
    chat_id: str
    content: str
    reply_to: str | None = None
    media: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
