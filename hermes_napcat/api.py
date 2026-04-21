"""OneBot 11 HTTP API async client."""
from __future__ import annotations

import logging
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)


async def call_onebot_api(
    base_url: str,
    action: str,
    params: dict[str, Any] | None = None,
    access_token: str | None = None,
    timeout: float = 10,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{action}"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=timeout)
    ) as session:
        async with session.post(url, json=params or {}, headers=headers) as resp:
            resp.raise_for_status()
            data: dict[str, Any] = await resp.json()
            if data.get("retcode", 0) != 0:
                raise RuntimeError(
                    f"OneBot API error {action}: retcode={data.get('retcode')} status={data.get('status')}"
                )
            return data


async def get_login_info(base_url: str, access_token: str | None = None) -> dict[str, Any]:
    resp = await call_onebot_api(base_url, "get_login_info", access_token=access_token)
    return resp["data"]


async def send_private_msg(
    base_url: str,
    user_id: int,
    message: list[dict],
    access_token: str | None = None,
) -> dict[str, Any]:
    resp = await call_onebot_api(
        base_url, "send_private_msg",
        {"user_id": user_id, "message": message},
        access_token=access_token,
    )
    return resp["data"]


async def send_group_msg(
    base_url: str,
    group_id: int,
    message: list[dict],
    access_token: str | None = None,
) -> dict[str, Any]:
    resp = await call_onebot_api(
        base_url, "send_group_msg",
        {"group_id": group_id, "message": message},
        access_token=access_token,
    )
    return resp["data"]


async def get_msg(
    base_url: str,
    message_id: int,
    access_token: str | None = None,
) -> dict[str, Any]:
    resp = await call_onebot_api(
        base_url, "get_msg",
        {"message_id": message_id},
        access_token=access_token,
    )
    return resp["data"]


async def upload_group_file(
    base_url: str,
    group_id: int,
    file: str,
    name: str,
    access_token: str | None = None,
) -> None:
    await call_onebot_api(
        base_url, "upload_group_file",
        {"group_id": group_id, "file": file, "name": name},
        access_token=access_token,
        timeout=60,
    )


async def upload_private_file(
    base_url: str,
    user_id: int,
    file: str,
    name: str,
    access_token: str | None = None,
) -> None:
    await call_onebot_api(
        base_url, "upload_private_file",
        {"user_id": user_id, "file": file, "name": name},
        access_token=access_token,
        timeout=60,
    )


# ---------- segment builders ----------

def text_segment(text: str) -> dict:
    return {"type": "text", "data": {"text": text}}

def image_segment(file_url: str) -> dict:
    return {"type": "image", "data": {"file": file_url}}

def at_segment(qq: int | str) -> dict:
    return {"type": "at", "data": {"qq": str(qq)}}

def reply_segment(message_id: int | str) -> dict:
    return {"type": "reply", "data": {"id": str(message_id)}}

def record_segment(file_url: str) -> dict:
    return {"type": "record", "data": {"file": file_url}}

def video_segment(file_url: str) -> dict:
    return {"type": "video", "data": {"file": file_url}}
