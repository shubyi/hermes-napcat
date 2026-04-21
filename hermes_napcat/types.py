"""OneBot 11 type definitions."""
from __future__ import annotations
from typing import Any, Optional
from typing_extensions import TypedDict


class OneBotSegment(TypedDict, total=False):
    type: str
    data: dict[str, Any]


class OneBotSender(TypedDict, total=False):
    user_id: int
    nickname: str
    card: str
    sex: str
    age: int
    role: str


class OneBotMessageEvent(TypedDict, total=False):
    time: int
    self_id: int
    post_type: str
    message_type: str
    sub_type: str
    message_id: int
    user_id: int
    group_id: int
    message: list[OneBotSegment]
    raw_message: str
    sender: OneBotSender


class OneBotLoginInfo(TypedDict):
    user_id: int
    nickname: str
