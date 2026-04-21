---
name: qq-napcat
description: Interact with QQ via the NapCat / OneBot 11 adapter. Use for sending messages, group management, file transfers, member info, notices, reactions, OCR, and translation.
version: 1.0.0
author: hermes-napcat
license: MIT
platforms: [linux]
prerequisites:
  services: [napcat, hermes-gateway]
metadata:
  hermes:
    tags: [qq, napcat, onebot, messaging, group-management, china]
    homepage: https://github.com/NapNeko/NapCatQQ
---

# QQ (NapCat / OneBot 11)

NapCat is a headless QQ client that exposes the OneBot 11 API. Hermes connects to it via a reverse WebSocket. All tools in this skill call the NapCat HTTP API and are prefixed `qq_`.

Use this skill for:
- Sending text, images, files, reactions, and merged-forward messages to groups or private chats
- Reading message history and essence (精华) message lists
- Group management: mute, kick, set admin, rename, set avatar, publish notices
- Member and friend info lookups
- Handling friend and group join requests
- Group file system operations
- Image OCR and QQ translation

---

## Admin System

Some tools are restricted to admins. Admins are configured in `~/.hermes/config.yaml`:

```yaml
platforms:
  napcat:
    extra:
      admins: ["123456789", "987654321"]
```

If `admins` is empty, **all users** can call any tool (open mode). When admins are set, non-admin callers receive: `Permission denied: only admins can use this command`.

**Admin-required tools:** `qq_mute_group_member`, `qq_kick_group_member`, `qq_set_group_admin`, `qq_set_group_name`, `qq_set_group_whole_ban`, `qq_leave_group`, `qq_set_group_portrait`, `qq_set_group_special_title`, `qq_set_essence_msg`, `qq_delete_essence_msg`, `qq_send_group_notice`, `qq_delete_group_notice`, `qq_delete_group_file`, `qq_delete_friend`, `qq_handle_friend_request`, `qq_handle_group_request`

---

## Message Format (OneBot 11 Segments)

The `message` parameter is always an **array of segment objects**. Common types:

```json
[{"type": "text", "data": {"text": "Hello!"}}]

[{"type": "image", "data": {"file": "/path/to/image.jpg"}}]
[{"type": "image", "data": {"file": "https://example.com/img.png"}}]

[{"type": "at", "data": {"qq": "123456789"}},
 {"type": "text", "data": {"text": " please check this"}}]

[{"type": "reply", "data": {"id": "MESSAGE_ID"}},
 {"type": "text", "data": {"text": "Replying to you"}}]

[{"type": "face", "data": {"id": "76"}}]

[{"type": "record", "data": {"file": "/path/to/audio.silk"}}]

[{"type": "video", "data": {"file": "/path/to/video.mp4"}}]
```

To send plain text, wrap it: `[{"type": "text", "data": {"text": "your message"}}]`

---

## Quick Reference

| Action | Tool |
|---|---|
| Send to group | `qq_send_message` (message_type=group) |
| Send to private | `qq_send_message` (message_type=private) |
| Recall a message | `qq_recall_message` |
| React with emoji | `qq_set_msg_emoji_like` |
| Mark as read | `qq_mark_msg_as_read` |
| Forward a message | `qq_forward_message` |
| Send merged-forward to group | `qq_send_group_forward_msg` |
| Send merged-forward to user | `qq_send_private_forward_msg` |
| Group message history | `qq_get_group_msg_history` |
| Friend message history | `qq_get_friend_msg_history` |
| Get essence messages | `qq_get_essence_msg_list` |
| Set essence message | `qq_set_essence_msg` ★ |
| Remove essence message | `qq_delete_essence_msg` ★ |
| Get user info | `qq_get_user_info` |
| Get friend list | `qq_get_friend_list` |
| Like a user's profile | `qq_like_user` |
| Poke a user | `qq_poke` |
| Set friend remark | `qq_set_friend_remark` |
| Delete friend | `qq_delete_friend` ★ |
| Accept/reject friend request | `qq_handle_friend_request` ★ |
| Get group info | `qq_get_group_info` |
| Get all groups | `qq_get_group_list` |
| Get member info | `qq_get_group_member_info` |
| Get all members | `qq_get_group_member_list` |
| Get group honors | `qq_get_group_honor_info` |
| Check @all quota | `qq_get_group_at_all_remain` |
| Mute member | `qq_mute_group_member` ★ |
| Kick member | `qq_kick_group_member` ★ |
| Set/revoke admin | `qq_set_group_admin` ★ |
| Rename group | `qq_set_group_name` ★ |
| Set member card (nickname) | `qq_set_group_card` |
| Whole-group mute | `qq_set_group_whole_ban` ★ |
| Set special title | `qq_set_group_special_title` ★ |
| Leave / dismiss group | `qq_leave_group` ★ |
| Group check-in (打卡) | `qq_set_group_sign` |
| Set group remark | `qq_set_group_remark` |
| Set group avatar | `qq_set_group_portrait` ★ |
| Accept/reject group request | `qq_handle_group_request` ★ |
| Publish group notice | `qq_send_group_notice` ★ |
| Get group notices | `qq_get_group_notice` |
| Delete group notice | `qq_delete_group_notice` ★ |
| Upload file | `qq_upload_file` |
| List group files | `qq_get_group_root_files` |
| Get file download URL | `qq_get_group_file_url` |
| Create folder | `qq_create_group_file_folder` |
| Delete group file | `qq_delete_group_file` ★ |
| Download a URL via NapCat | `qq_download_file` |
| OCR image | `qq_ocr_image` |
| Translate EN→ZH | `qq_translate_en2zh` |

★ = requires admin (see Admin System section)

---

## Tool Details

### Messaging

**Send a message**
```
qq_send_message(
  message_type = "group" | "private",
  group_id     = "GROUP_ID",          # required when message_type=group
  user_id      = "QQ_NUMBER",         # required when message_type=private
  message      = [{"type": "text", "data": {"text": "Hello!"}}]
)
```

**Recall a message** (within 2 minutes — QQ protocol limit)
```
qq_recall_message(message_id = "MESSAGE_ID")
```

**React with emoji**
```
qq_set_msg_emoji_like(message_id = "MESSAGE_ID", emoji_id = "76")
```
Common emoji IDs: 76 = 赞(thumbs up), 66 = 爱心, 277 = 烟花, 212 = 强, 4 = 撇嘴

**Forward a single message**
```
qq_forward_message(message_id = "MESSAGE_ID", group_id = "GROUP_ID")
qq_forward_message(message_id = "MESSAGE_ID", user_id  = "QQ_NUMBER")
```

**Send merged-forward (合并转发)**
```
qq_send_group_forward_msg(
  group_id = "GROUP_ID",
  messages = [
    {
      "type": "node",
      "data": {
        "name": "Display Name",
        "uin": "QQ_NUMBER",
        "content": [{"type": "text", "data": {"text": "Message content"}}]
      }
    }
  ]
)
```

---

### Message History & Essence

**Group message history**
```
qq_get_group_msg_history(group_id = "GROUP_ID", count = 20)
qq_get_group_msg_history(group_id = "GROUP_ID", message_id = "MSG_ID", count = 20)
```
Use `message_id` to paginate backwards (fetch messages before that ID).

**Friend message history**
```
qq_get_friend_msg_history(user_id = "QQ_NUMBER", count = 20)
```

**Essence messages (精华消息)**
```
qq_get_essence_msg_list(group_id = "GROUP_ID")
qq_set_essence_msg(message_id = "MESSAGE_ID")      # admin required
qq_delete_essence_msg(message_id = "MESSAGE_ID")   # admin required
```

---

### User & Friend Info

```
qq_get_user_info(user_id = "QQ_NUMBER")          # nickname, avatar, etc.
qq_get_friend_list()                              # bot's friend list
qq_like_user(user_id = "QQ_NUMBER", times = 1)   # max 10 likes/day per user
qq_poke(user_id = "QQ_NUMBER")                   # private poke
qq_poke(user_id = "QQ_NUMBER", group_id = "G")   # group poke
qq_set_friend_remark(user_id = "QQ_NUMBER", remark = "Nick")
qq_delete_friend(user_id = "QQ_NUMBER")           # admin required
```

**Handle friend request** (from a `friend_request` event)
```
qq_handle_friend_request(flag = "FLAG_FROM_EVENT", approve = true, remark = "")
```

---

### Group Info

```
qq_get_group_info(group_id = "GROUP_ID")
qq_get_group_list()
qq_get_group_member_info(group_id = "GROUP_ID", user_id = "QQ_NUMBER")
qq_get_group_member_list(group_id = "GROUP_ID")
qq_get_group_honor_info(group_id = "GROUP_ID", type = "all")
qq_get_group_at_all_remain(group_id = "GROUP_ID")
```

`type` for honor info: `talkative` (龙王) | `performer` | `legend` | `strong_newbie` | `emotion` | `all`

---

### Group Management (admin-required ★)

**Mute / unmute a member**
```
qq_mute_group_member(group_id = "G", user_id = "U", duration = 600)
qq_mute_group_member(group_id = "G", user_id = "U", duration = 0)   # unmute
```
Duration is seconds. Common durations: 600 (10 min), 3600 (1h), 86400 (1 day), 2592000 (30 days)

**Kick**
```
qq_kick_group_member(group_id = "G", user_id = "U", reject_add_request = false)
```

**Admin role**
```
qq_set_group_admin(group_id = "G", user_id = "U", enable = true)   # grant
qq_set_group_admin(group_id = "G", user_id = "U", enable = false)  # revoke
```
Only the group owner can grant/revoke admin.

**Rename, card, title**
```
qq_set_group_name(group_id = "G", group_name = "New Name")
qq_set_group_card(group_id = "G", user_id = "U", card = "Nickname")   # blank to reset
qq_set_group_special_title(group_id = "G", user_id = "U", special_title = "VIP")  # owner only
```

**Whole-group mute**
```
qq_set_group_whole_ban(group_id = "G", enable = true)
qq_set_group_whole_ban(group_id = "G", enable = false)
```

**Leave or dismiss**
```
qq_leave_group(group_id = "G")                         # leave
qq_leave_group(group_id = "G", is_dismiss = true)      # dismiss (bot must be owner)
```

**Group avatar**
```
qq_set_group_portrait(group_id = "G", file = "/path/to/avatar.jpg")
```

**Handle join request** (from a `group_request` event)
```
qq_handle_group_request(flag = "FLAG", sub_type = "add",    approve = true)
qq_handle_group_request(flag = "FLAG", sub_type = "invite", approve = true)
qq_handle_group_request(flag = "FLAG", sub_type = "add",    approve = false, reason = "Not accepting")
```

---

### Group Notices (公告)

```
qq_send_group_notice(group_id = "G", content = "Announcement text")         # admin ★
qq_send_group_notice(group_id = "G", content = "With image", image = "/path/img.jpg")
qq_get_group_notice(group_id = "G")
qq_delete_group_notice(group_id = "G", notice_id = "NOTICE_ID")             # admin ★
```

---

### File Operations

**Upload**
```
qq_upload_file(file = "/path/to/file.pdf", group_id = "G")        # to group
qq_upload_file(file = "/path/to/file.zip", user_id = "QQ_NUMBER") # to private chat
qq_upload_file(file = "/path/to/file.pdf", group_id = "G", name = "report.pdf", folder_id = "FOLDER_ID")
```

**Browse and download group files**
```
qq_get_group_root_files(group_id = "G")                            # list root
qq_get_group_file_url(group_id = "G", file_id = "FILE_ID")         # get download URL
qq_create_group_file_folder(group_id = "G", name = "Docs")
qq_delete_group_file(group_id = "G", file_id = "FILE_ID")          # admin ★
```

**Download any URL through NapCat** (useful when direct download is unavailable)
```
qq_download_file(url = "https://example.com/file.pdf")
# Returns: {"file": "/local/path/to/downloaded/file"}
```

---

### Misc

**OCR an image**
```
qq_ocr_image(image = "/path/to/image.jpg")
qq_ocr_image(image = "https://example.com/img.png")
# Returns: {"texts": [...], "language": "zh"}
```

**Translate English to Chinese**
```
qq_translate_en2zh(content = "Hello world")
```

**Group check-in (打卡)**
```
qq_set_group_sign(group_id = "G")
```

**Set group remark (personal note, not visible to others)**
```
qq_set_group_remark(group_id = "G", remark = "Work group")
```

---

## Common Workflows

### Reply to a message in a group
The incoming event includes `message_id` and `group_id`. Quote-reply by prepending a reply segment:
```
qq_send_message(
  message_type = "group",
  group_id     = "GROUP_ID",
  message      = [
    {"type": "reply", "data": {"id": "ORIGINAL_MESSAGE_ID"}},
    {"type": "text",  "data": {"text": "Here is my response"}}
  ]
)
```

### @ a user in a group message
```
qq_send_message(
  message_type = "group",
  group_id     = "GROUP_ID",
  message      = [
    {"type": "at",   "data": {"qq": "TARGET_QQ_NUMBER"}},
    {"type": "text", "data": {"text": " please read this"}}
  ]
)
```

### Send an image
```
qq_send_message(
  message_type = "group",
  group_id     = "GROUP_ID",
  message      = [{"type": "image", "data": {"file": "/path/to/image.jpg"}}]
)
```

### Mute then notify
```
qq_mute_group_member(group_id = "G", user_id = "U", duration = 3600)
qq_send_message(
  message_type = "group",
  group_id     = "G",
  message      = [{"type": "text", "data": {"text": "User has been muted for 1 hour."}}]
)
```

### Look up who is currently the most active (龙王)
```
qq_get_group_honor_info(group_id = "GROUP_ID", type = "talkative")
```

### Read group chat history before responding
```
qq_get_group_msg_history(group_id = "GROUP_ID", count = 20)
```
Parse the returned `messages` array. Each entry has: `message_id`, `sender.user_id`, `sender.nickname`, `time`, and `message` (array of segments).

---

## Protocol Limits & Notes

| Constraint | Detail |
|---|---|
| Recall window | **2 minutes** — `qq_recall_message` fails after that |
| Profile likes | Max **10 per day** per target user (`qq_like_user times ≤ 10`) |
| @all quota | Limited per group per day; check with `qq_get_group_at_all_remain` |
| Special title | Bot must be **group owner** (not just admin) |
| Group dismiss | Bot must be **group owner** (`is_dismiss=true`) |
| Mute duration | 0 = unmute; max is ~2592000 s (30 days) |
| Admin grant | Only **group owner** can set admin; admin cannot grant admin to others |
| File upload size | Depends on QQ account level; typically ≤ 100 MB for regular accounts |

---

## Agent Workflow

1. Identify whether the request is for a **group** or **private** conversation from context.
2. For **management actions** (mute, kick, admin, notice, etc.), confirm the sender is an admin before calling — the tool will reject non-admins anyway, but confirming first avoids a wasted call.
3. For **irreversible actions** (kick with `reject_add_request=true`, dismiss group, delete friend), briefly confirm with the user before proceeding.
4. When the user asks to "reply" to a message, use a `reply` segment pointing to the original `message_id` — do not just send plain text.
5. For bulk history reads, use `qq_get_group_msg_history` with `count ≤ 50` to avoid overloading context.
6. When sending images or files, prefer local paths if the file is already on disk; use URLs only when the file is remote.
7. The `message_id` in incoming events is the value to pass to `qq_recall_message`, `qq_set_essence_msg`, etc.

---

## Error Handling

| Symptom | Likely Cause | Fix |
|---|---|---|
| `NapCat HTTP API not configured` | Adapter not running or misconfigured | Check `~/.hermes/config.yaml` `platforms.napcat.extra.http_api`; restart gateway |
| `Permission denied: only admins can use this command` | Caller not in admins list | Add caller's QQ to `admins` in config, or leave `admins: []` for open mode |
| `OneBot API error: RETCODE=100` | Invalid parameter (wrong ID type, missing field) | Check group_id/user_id are numeric strings |
| `OneBot API error: RETCODE=1000` | NapCat internal error (usually rate limit or QQ restrictions) | Wait and retry; check if bot has sufficient permissions in the group |
| Recall fails | Message older than 2 minutes, or not sent by the bot | QQ protocol limitation — cannot recall others' messages |
| Admin grant fails | Bot is not the group owner | Only owners can manage admins |
| File upload fails | File too large or NapCat lacks disk space | Check file size; NapCat downloads to `~/Napcat` |
