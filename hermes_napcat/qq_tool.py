"""QQ (NapCat / OneBot 11) tools for Hermes Agent.

Installed by ``hermes-napcat install`` to: tools/qq_tool.py

The NapCat adapter calls ``_init()`` at startup to supply the HTTP API URL
and access token.  All handlers are async (is_async=True).
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from tools.registry import registry, tool_error, tool_result

logger = logging.getLogger(__name__)

# ── Runtime config (injected by NapCatAdapter.__init__) ───────────────────────

_http_api: str = ""
_access_token: str = ""
_admins: list[str] = []
_current_sender: str = ""


def _init(http_api: str, access_token: str = "", admins: list[str] | None = None) -> None:
    global _http_api, _access_token, _admins
    _http_api = http_api.rstrip("/")
    _access_token = access_token
    _admins = [str(x) for x in (admins or [])]


def _set_context(sender_id: str) -> None:
    """Called by the adapter before each message is processed."""
    global _current_sender
    _current_sender = str(sender_id)


def _check() -> str | None:
    """Return an error string if the tool is not ready, else None."""
    if not _http_api:
        return "NapCat HTTP API not configured. Is the NapCat adapter running?"
    return None


def _require_admin() -> str | None:
    """Return an error string if the current sender is not an admin.

    If no admins are configured, all senders are allowed (open mode).
    """
    if not _admins:
        return None
    if _current_sender not in _admins:
        return f"Permission denied: only admins can use this command (sender: {_current_sender})."
    return None


# ── Core HTTP helper ───────────────────────────────────────────────────────────

async def _call(endpoint: str, **params: Any) -> dict:
    url = f"{_http_api}/{endpoint}"
    headers = {"Content-Type": "application/json"}
    if _access_token:
        headers["Authorization"] = f"Bearer {_access_token}"
    body = {k: v for k, v in params.items() if v is not None}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json=body, headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            data = await resp.json(content_type=None)
    retcode = data.get("retcode", 0)
    if retcode != 0:
        msg = data.get("message") or data.get("msg") or f"retcode={retcode}"
        raise RuntimeError(f"OneBot API error ({endpoint}): {msg}")
    return data.get("data") or {}


# ── Schema helpers ─────────────────────────────────────────────────────────────

def _schema(name: str, desc: str, props: dict, required: list[str] | None = None) -> dict:
    return {
        "name": name,
        "description": desc,
        "parameters": {
            "type": "object",
            "properties": props,
            "required": required or [],
        },
    }


def _str(desc: str) -> dict:
    return {"type": "string", "description": desc}


def _int(desc: str) -> dict:
    return {"type": "integer", "description": desc}


def _bool(desc: str) -> dict:
    return {"type": "boolean", "description": desc}


# ══════════════════════════════════════════════════════════════════════════════
# 1. MESSAGING
# ══════════════════════════════════════════════════════════════════════════════

async def _qq_send_message(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "send_msg",
            message_type=args.get("message_type"),
            group_id=args.get("group_id"),
            user_id=args.get("user_id"),
            message=args["message"],
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_send_message",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_send_message,
    schema=_schema(
        "qq_send_message",
        "Send a QQ message to a group or private chat. "
        "message is a list of OneBot 11 segments, e.g. [{\"type\":\"text\",\"data\":{\"text\":\"hello\"}}].",
        {
            "message_type": _str("'group' or 'private'"),
            "group_id": _str("Group ID (required when message_type=group)"),
            "user_id": _str("User QQ number (required when message_type=private)"),
            "message": {
                "type": "array",
                "description": "OneBot 11 message segments",
                "items": {"type": "object"},
            },
        },
        required=["message_type", "message"],
    ),
)


async def _qq_recall_message(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        await _call("delete_msg", message_id=int(args["message_id"]))
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_recall_message",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_recall_message,
    schema=_schema(
        "qq_recall_message", "Recall (unsend) a QQ message by its message_id.",
        {"message_id": _str("Message ID to recall")},
        required=["message_id"],
    ),
)


async def _qq_mark_msg_as_read(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        await _call("mark_msg_as_read", message_id=int(args["message_id"]))
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_mark_msg_as_read",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_mark_msg_as_read,
    schema=_schema(
        "qq_mark_msg_as_read", "Mark a message as read.",
        {"message_id": _str("Message ID")},
        required=["message_id"],
    ),
)


async def _qq_set_msg_emoji_like(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_msg_emoji_like",
            message_id=int(args["message_id"]),
            emoji_id=str(args["emoji_id"]),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_msg_emoji_like",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_msg_emoji_like,
    schema=_schema(
        "qq_set_msg_emoji_like", "React to a message with an emoji (QQ emoji ID).",
        {
            "message_id": _str("Message ID"),
            "emoji_id": _str("QQ emoji ID (integer as string, e.g. '76' for 赞)"),
        },
        required=["message_id", "emoji_id"],
    ),
)


async def _qq_forward_message(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "forward_friend_single_msg" if args.get("user_id") else "forward_group_single_msg",
            message_id=int(args["message_id"]),
            group_id=args.get("group_id"),
            user_id=args.get("user_id"),
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_forward_message",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_forward_message,
    schema=_schema(
        "qq_forward_message", "Forward a single message to a group or private chat.",
        {
            "message_id": _str("Message ID to forward"),
            "group_id": _str("Destination group ID"),
            "user_id": _str("Destination user QQ number"),
        },
        required=["message_id"],
    ),
)


async def _qq_send_group_forward_msg(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "send_group_forward_msg",
            group_id=int(args["group_id"]),
            messages=args["messages"],
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_send_group_forward_msg",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_send_group_forward_msg,
    schema=_schema(
        "qq_send_group_forward_msg",
        "Send a merged-forward message to a group. messages is a list of forward node segments.",
        {
            "group_id": _str("Target group ID"),
            "messages": {
                "type": "array",
                "description": "List of forward node segments",
                "items": {"type": "object"},
            },
        },
        required=["group_id", "messages"],
    ),
)


async def _qq_send_private_forward_msg(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "send_private_forward_msg",
            user_id=int(args["user_id"]),
            messages=args["messages"],
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_send_private_forward_msg",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_send_private_forward_msg,
    schema=_schema(
        "qq_send_private_forward_msg",
        "Send a merged-forward message to a private chat.",
        {
            "user_id": _str("Target user QQ number"),
            "messages": {
                "type": "array",
                "description": "List of forward node segments",
                "items": {"type": "object"},
            },
        },
        required=["user_id", "messages"],
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 2. MESSAGE HISTORY & ESSENCE
# ══════════════════════════════════════════════════════════════════════════════

async def _qq_get_group_msg_history(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "get_group_msg_history",
            group_id=int(args["group_id"]),
            message_id=args.get("message_id"),
            count=int(args.get("count", 20)),
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_msg_history",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_msg_history,
    schema=_schema(
        "qq_get_group_msg_history", "Fetch recent message history from a group.",
        {
            "group_id": _str("Group ID"),
            "message_id": _str("Fetch messages before this message_id (optional)"),
            "count": _int("Number of messages to fetch (default 20, max 100)"),
        },
        required=["group_id"],
    ),
)


async def _qq_get_friend_msg_history(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "get_friend_msg_history",
            user_id=int(args["user_id"]),
            message_id=args.get("message_id"),
            count=int(args.get("count", 20)),
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_friend_msg_history",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_friend_msg_history,
    schema=_schema(
        "qq_get_friend_msg_history", "Fetch recent message history with a friend.",
        {
            "user_id": _str("Friend QQ number"),
            "message_id": _str("Fetch messages before this message_id (optional)"),
            "count": _int("Number of messages to fetch (default 20)"),
        },
        required=["user_id"],
    ),
)


async def _qq_get_essence_msg_list(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("get_essence_msg_list", group_id=int(args["group_id"]))
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_essence_msg_list",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_essence_msg_list,
    schema=_schema(
        "qq_get_essence_msg_list", "Get the list of essence (pinned highlight) messages in a group.",
        {"group_id": _str("Group ID")},
        required=["group_id"],
    ),
)


async def _qq_set_essence_msg(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call("set_essence_msg", message_id=int(args["message_id"]))
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_essence_msg",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_essence_msg,
    schema=_schema(
        "qq_set_essence_msg", "Set a message as an essence (highlight) message in a group. Requires admin.",
        {"message_id": _str("Message ID")},
        required=["message_id"],
    ),
)


async def _qq_delete_essence_msg(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call("delete_essence_msg", message_id=int(args["message_id"]))
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_delete_essence_msg",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_delete_essence_msg,
    schema=_schema(
        "qq_delete_essence_msg", "Remove a message from the group's essence list. Requires admin.",
        {"message_id": _str("Message ID")},
        required=["message_id"],
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 3. USER & FRIEND INFO
# ══════════════════════════════════════════════════════════════════════════════

async def _qq_get_user_info(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("get_stranger_info", user_id=int(args["user_id"]))
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_user_info",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_user_info,
    schema=_schema(
        "qq_get_user_info", "Get basic info (nickname, avatar, etc.) for any QQ user.",
        {"user_id": _str("QQ number")},
        required=["user_id"],
    ),
)


async def _qq_get_friend_list(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("get_friend_list")
        return tool_result(data if isinstance(data, list) else [data])
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_friend_list",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_friend_list,
    schema=_schema("qq_get_friend_list", "Get the bot's friend list.", {}),
)


async def _qq_like_user(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        await _call(
            "send_like",
            user_id=int(args["user_id"]),
            times=int(args.get("times", 1)),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_like_user",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_like_user,
    schema=_schema(
        "qq_like_user", "Send a profile like to a QQ user.",
        {
            "user_id": _str("QQ number to like"),
            "times": _int("Number of likes to send (default 1, max 10 per day)"),
        },
        required=["user_id"],
    ),
)


async def _qq_set_friend_remark(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_friend_add_request",
            user_id=int(args["user_id"]),
            remark=args.get("remark", ""),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_friend_remark",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_friend_remark,
    schema=_schema(
        "qq_set_friend_remark", "Set or clear the remark (alias) for a friend.",
        {
            "user_id": _str("Friend QQ number"),
            "remark": _str("New remark (blank to clear)"),
        },
        required=["user_id"],
    ),
)


async def _qq_delete_friend(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call("delete_friend", user_id=int(args["user_id"]))
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_delete_friend",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_delete_friend,
    schema=_schema(
        "qq_delete_friend", "Delete a friend. Requires admin.",
        {"user_id": _str("Friend QQ number to remove")},
        required=["user_id"],
    ),
)


async def _qq_handle_friend_request(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_friend_add_request",
            flag=args["flag"],
            approve=args.get("approve", True),
            remark=args.get("remark", ""),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_handle_friend_request",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_handle_friend_request,
    schema=_schema(
        "qq_handle_friend_request", "Accept or reject an incoming friend request. Requires admin.",
        {
            "flag": _str("Request flag from the friend_request event"),
            "approve": _bool("True to accept, False to reject (default True)"),
            "remark": _str("Remark to set on accept (optional)"),
        },
        required=["flag"],
    ),
)


async def _qq_poke(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        await _call(
            "group_poke" if args.get("group_id") else "friend_poke",
            user_id=int(args["user_id"]),
            group_id=args.get("group_id"),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_poke",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_poke,
    schema=_schema(
        "qq_poke", "Poke (nudge) a user in a group or private chat.",
        {
            "user_id": _str("Target QQ number"),
            "group_id": _str("Group ID (omit for private poke)"),
        },
        required=["user_id"],
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 4. GROUP INFO
# ══════════════════════════════════════════════════════════════════════════════

async def _qq_get_group_info(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("get_group_info", group_id=int(args["group_id"]))
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_info",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_info,
    schema=_schema(
        "qq_get_group_info", "Get basic info for a QQ group (name, member count, etc.).",
        {"group_id": _str("Group ID")},
        required=["group_id"],
    ),
)


async def _qq_get_group_list(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("get_group_list")
        return tool_result(data if isinstance(data, list) else [data])
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_list",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_list,
    schema=_schema("qq_get_group_list", "Get the list of all groups the bot has joined.", {}),
)


async def _qq_get_group_member_info(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "get_group_member_info",
            group_id=int(args["group_id"]),
            user_id=int(args["user_id"]),
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_member_info",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_member_info,
    schema=_schema(
        "qq_get_group_member_info", "Get detailed info for a group member.",
        {
            "group_id": _str("Group ID"),
            "user_id": _str("Member QQ number"),
        },
        required=["group_id", "user_id"],
    ),
)


async def _qq_get_group_member_list(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("get_group_member_list", group_id=int(args["group_id"]))
        return tool_result(data if isinstance(data, list) else [data])
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_member_list",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_member_list,
    schema=_schema(
        "qq_get_group_member_list", "List all members of a group.",
        {"group_id": _str("Group ID")},
        required=["group_id"],
    ),
)


async def _qq_get_group_honor_info(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "get_group_honor_info",
            group_id=int(args["group_id"]),
            type=args.get("type", "all"),
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_honor_info",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_honor_info,
    schema=_schema(
        "qq_get_group_honor_info",
        "Get honor info (龙王/群聊之火/etc.) for a group.",
        {
            "group_id": _str("Group ID"),
            "type": _str("Honor type: talkative | performer | legend | strong_newbie | emotion | all (default)"),
        },
        required=["group_id"],
    ),
)


async def _qq_get_group_at_all_remain(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("get_group_at_all_remain", group_id=int(args["group_id"]))
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_at_all_remain",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_at_all_remain,
    schema=_schema(
        "qq_get_group_at_all_remain",
        "Check remaining @all usage count for a group today.",
        {"group_id": _str("Group ID")},
        required=["group_id"],
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 5. GROUP MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

async def _qq_mute_group_member(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_ban",
            group_id=int(args["group_id"]),
            user_id=int(args["user_id"]),
            duration=int(args.get("duration", 600)),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_mute_group_member",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_mute_group_member,
    schema=_schema(
        "qq_mute_group_member", "Mute a group member for a given duration (0 = unmute). Requires admin.",
        {
            "group_id": _str("Group ID"),
            "user_id": _str("Member QQ number"),
            "duration": _int("Mute duration in seconds (0 = unmute, default 600)"),
        },
        required=["group_id", "user_id"],
    ),
)


async def _qq_kick_group_member(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_kick",
            group_id=int(args["group_id"]),
            user_id=int(args["user_id"]),
            reject_add_request=args.get("reject_add_request", False),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_kick_group_member",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_kick_group_member,
    schema=_schema(
        "qq_kick_group_member", "Kick a member from a group. Requires admin.",
        {
            "group_id": _str("Group ID"),
            "user_id": _str("Member QQ number"),
            "reject_add_request": _bool("Also block them from rejoining (default false)"),
        },
        required=["group_id", "user_id"],
    ),
)


async def _qq_set_group_admin(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_admin",
            group_id=int(args["group_id"]),
            user_id=int(args["user_id"]),
            enable=args.get("enable", True),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_group_admin",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_group_admin,
    schema=_schema(
        "qq_set_group_admin", "Grant or revoke group admin for a member. Requires admin.",
        {
            "group_id": _str("Group ID"),
            "user_id": _str("Member QQ number"),
            "enable": _bool("True = grant admin, False = revoke (default True)"),
        },
        required=["group_id", "user_id"],
    ),
)


async def _qq_set_group_name(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_name",
            group_id=int(args["group_id"]),
            group_name=args["group_name"],
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_group_name",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_group_name,
    schema=_schema(
        "qq_set_group_name", "Rename a group. Requires admin.",
        {
            "group_id": _str("Group ID"),
            "group_name": _str("New group name"),
        },
        required=["group_id", "group_name"],
    ),
)


async def _qq_set_group_card(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_card",
            group_id=int(args["group_id"]),
            user_id=int(args["user_id"]),
            card=args.get("card", ""),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_group_card",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_group_card,
    schema=_schema(
        "qq_set_group_card", "Set or clear a member's in-group nickname (card).",
        {
            "group_id": _str("Group ID"),
            "user_id": _str("Member QQ number"),
            "card": _str("New nickname (blank to reset to real name)"),
        },
        required=["group_id", "user_id"],
    ),
)


async def _qq_set_group_whole_ban(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_whole_ban",
            group_id=int(args["group_id"]),
            enable=args.get("enable", True),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_group_whole_ban",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_group_whole_ban,
    schema=_schema(
        "qq_set_group_whole_ban", "Enable or disable whole-group mute. Requires admin.",
        {
            "group_id": _str("Group ID"),
            "enable": _bool("True = mute all, False = unmute all (default True)"),
        },
        required=["group_id"],
    ),
)


async def _qq_set_group_special_title(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_special_title",
            group_id=int(args["group_id"]),
            user_id=int(args["user_id"]),
            special_title=args.get("special_title", ""),
            duration=-1,
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_group_special_title",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_group_special_title,
    schema=_schema(
        "qq_set_group_special_title", "Set a custom special title for a group member (owner only). Requires admin.",
        {
            "group_id": _str("Group ID"),
            "user_id": _str("Member QQ number"),
            "special_title": _str("Title text (blank to clear)"),
        },
        required=["group_id", "user_id"],
    ),
)


async def _qq_leave_group(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_leave",
            group_id=int(args["group_id"]),
            is_dismiss=args.get("is_dismiss", False),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_leave_group",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_leave_group,
    schema=_schema(
        "qq_leave_group", "Leave a group (or dismiss it if the bot is the owner). Requires admin.",
        {
            "group_id": _str("Group ID"),
            "is_dismiss": _bool("True to dismiss the group (bot must be owner)"),
        },
        required=["group_id"],
    ),
)


async def _qq_set_group_sign(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        await _call("send_group_sign", group_id=int(args["group_id"]))
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_group_sign",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_group_sign,
    schema=_schema(
        "qq_set_group_sign", "Perform group sign-in (打卡).",
        {"group_id": _str("Group ID")},
        required=["group_id"],
    ),
)


async def _qq_set_group_remark(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_remark",
            group_id=int(args["group_id"]),
            remark=args.get("remark", ""),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_group_remark",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_group_remark,
    schema=_schema(
        "qq_set_group_remark", "Set a personal remark for a group (visible only to you).",
        {
            "group_id": _str("Group ID"),
            "remark": _str("Remark text (blank to clear)"),
        },
        required=["group_id"],
    ),
)


async def _qq_set_group_portrait(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_portrait",
            group_id=int(args["group_id"]),
            file=args["file"],
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_set_group_portrait",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_set_group_portrait,
    schema=_schema(
        "qq_set_group_portrait", "Set the group avatar (owner/admin only). Requires admin.",
        {
            "group_id": _str("Group ID"),
            "file": _str("Image file path or URL"),
        },
        required=["group_id", "file"],
    ),
)


async def _qq_handle_group_request(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "set_group_add_request",
            flag=args["flag"],
            sub_type=args.get("sub_type", "add"),
            approve=args.get("approve", True),
            reason=args.get("reason", ""),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_handle_group_request",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_handle_group_request,
    schema=_schema(
        "qq_handle_group_request", "Accept or reject a group join request or group invite. Requires admin.",
        {
            "flag": _str("Request flag from the group_request event"),
            "sub_type": _str("'add' for join request, 'invite' for bot invite (default 'add')"),
            "approve": _bool("True to approve, False to reject (default True)"),
            "reason": _str("Rejection reason (only used when approve=False)"),
        },
        required=["flag"],
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 6. GROUP NOTICES
# ══════════════════════════════════════════════════════════════════════════════

async def _qq_send_group_notice(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "_send_group_notice",
            group_id=int(args["group_id"]),
            content=args["content"],
            image=args.get("image", ""),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_send_group_notice",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_send_group_notice,
    schema=_schema(
        "qq_send_group_notice", "Publish a group announcement. Requires admin.",
        {
            "group_id": _str("Group ID"),
            "content": _str("Announcement text"),
            "image": _str("Optional image path or URL to attach"),
        },
        required=["group_id", "content"],
    ),
)


async def _qq_get_group_notice(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("_get_group_notice", group_id=int(args["group_id"]))
        return tool_result(data if isinstance(data, list) else [data])
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_notice",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_notice,
    schema=_schema(
        "qq_get_group_notice", "Get the list of group announcements.",
        {"group_id": _str("Group ID")},
        required=["group_id"],
    ),
)


async def _qq_delete_group_notice(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "_del_group_notice",
            group_id=int(args["group_id"]),
            notice_id=args["notice_id"],
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_delete_group_notice",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_delete_group_notice,
    schema=_schema(
        "qq_delete_group_notice", "Delete a group announcement. Requires admin.",
        {
            "group_id": _str("Group ID"),
            "notice_id": _str("Notice ID (from qq_get_group_notice)"),
        },
        required=["group_id", "notice_id"],
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 7. FILE OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

async def _qq_upload_file(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        if args.get("group_id"):
            data = await _call(
                "upload_group_file",
                group_id=int(args["group_id"]),
                file=args["file"],
                name=args.get("name", ""),
                folder_id=args.get("folder_id", ""),
            )
        else:
            data = await _call(
                "upload_private_file",
                user_id=int(args["user_id"]),
                file=args["file"],
                name=args.get("name", ""),
            )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_upload_file",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_upload_file,
    schema=_schema(
        "qq_upload_file", "Upload a file to a group or private chat.",
        {
            "file": _str("Local file path or URL"),
            "name": _str("Display name for the file"),
            "group_id": _str("Upload to this group (mutually exclusive with user_id)"),
            "user_id": _str("Upload to this user's private chat"),
            "folder_id": _str("Target folder ID within the group (optional)"),
        },
        required=["file"],
    ),
)


async def _qq_get_group_root_files(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("get_group_root_files", group_id=int(args["group_id"]))
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_root_files",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_root_files,
    schema=_schema(
        "qq_get_group_root_files", "List files and folders in a group's root file directory.",
        {"group_id": _str("Group ID")},
        required=["group_id"],
    ),
)


async def _qq_get_group_file_url(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "get_group_file_url",
            group_id=int(args["group_id"]),
            file_id=args["file_id"],
            busid=int(args.get("busid", 0)),
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_get_group_file_url",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_get_group_file_url,
    schema=_schema(
        "qq_get_group_file_url", "Get a temporary download URL for a group file.",
        {
            "group_id": _str("Group ID"),
            "file_id": _str("File ID (from qq_get_group_root_files)"),
            "busid": _int("busid from the file listing (default 0)"),
        },
        required=["group_id", "file_id"],
    ),
)


async def _qq_create_group_file_folder(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "create_group_file_folder",
            group_id=int(args["group_id"]),
            name=args["name"],
            parent_id=args.get("parent_id", "/"),
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_create_group_file_folder",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_create_group_file_folder,
    schema=_schema(
        "qq_create_group_file_folder", "Create a folder in the group file system.",
        {
            "group_id": _str("Group ID"),
            "name": _str("Folder name"),
            "parent_id": _str("Parent folder ID (default '/' for root)"),
        },
        required=["group_id", "name"],
    ),
)


async def _qq_delete_group_file(args: dict, **_) -> str:
    err = _check() or _require_admin()
    if err:
        return tool_error(err)
    try:
        await _call(
            "delete_group_file",
            group_id=int(args["group_id"]),
            file_id=args["file_id"],
            busid=int(args.get("busid", 0)),
        )
        return tool_result(success=True)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_delete_group_file",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_delete_group_file,
    schema=_schema(
        "qq_delete_group_file", "Delete a file from the group file system. Requires admin.",
        {
            "group_id": _str("Group ID"),
            "file_id": _str("File ID"),
            "busid": _int("busid from the file listing (default 0)"),
        },
        required=["group_id", "file_id"],
    ),
)


async def _qq_download_file(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call(
            "download_file",
            url=args["url"],
            thread_count=int(args.get("thread_count", 1)),
            headers=args.get("headers", ""),
        )
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_download_file",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_download_file,
    schema=_schema(
        "qq_download_file",
        "Ask NapCat to download a file from a URL and return the local path.",
        {
            "url": _str("URL to download"),
            "thread_count": _int("Download threads (default 1)"),
            "headers": _str("Extra HTTP headers as a string (optional)"),
        },
        required=["url"],
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 8. MISC
# ══════════════════════════════════════════════════════════════════════════════

async def _qq_ocr_image(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("ocr_image", image=args["image"])
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_ocr_image",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_ocr_image,
    schema=_schema(
        "qq_ocr_image", "Run OCR on an image and return the recognized text.",
        {"image": _str("Image file path or URL")},
        required=["image"],
    ),
)


async def _qq_translate_en2zh(args: dict, **_) -> str:
    err = _check()
    if err:
        return tool_error(err)
    try:
        data = await _call("get_word_slices", content=args["content"])
        return tool_result(data)
    except Exception as e:
        return tool_error(str(e))

registry.register(
    name="qq_translate_en2zh",
    toolset="napcat",
    is_async=True,
    emoji="🐧",
    handler=_qq_translate_en2zh,
    schema=_schema(
        "qq_translate_en2zh", "Translate English text to Chinese using the QQ translation service.",
        {"content": _str("English text to translate")},
        required=["content"],
    ),
)
