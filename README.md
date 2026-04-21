# hermes-napcat

[English](README.md) | [中文](README.zh.md)

**NapCat (QQ / OneBot 11) platform adapter for [Hermes Agent](https://github.com/NousResearch/hermes-agent)**

Connect Hermes to QQ via [NapCat](https://github.com/NapNeko/NapCatQQ)'s OneBot 11 reverse WebSocket. Chat with your Hermes AI assistant in any QQ group or DM, with full group management capabilities.

```
QQ App ──── NapCat ──WS──▶ hermes-napcat ──▶ Hermes (LLM)
                                │                  │
                                └─────HTTP API ◀───┘
                               (port 18801)   (port 18800)
```

---

## Features

- **Group & DM support** — @mention in groups, direct message for private chats
- **Per-group shared sessions** — the whole group shares one conversation context; sender name is automatically prefixed so the AI knows who said what
- **Admin system** — restrict management commands (mute, kick, etc.) to a configurable list of QQ numbers
- **48 QQ management tools** — messaging, group management, file operations, OCR, reactions, and more
- **Media support** — images, voice messages (→ WAV via ffmpeg), video, file upload/download
- **Quoted message context** — replies include the quoted text for full conversation context
- **One-command setup** — interactive wizard installs and configures everything

---

## Requirements

- Python 3.11+
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) (source install)
- [NapCat](https://github.com/NapNeko/NapCatQQ) running with HTTP API + reverse WS
- `aiohttp >= 3.9`
- `ffmpeg` (optional, for voice message transcription)

---

## Installation

### 1. Install the package

```bash
pip install hermes-napcat
```

### 2. Run the setup wizard

```bash
hermes-napcat setup
```

The wizard will:
- Patch Hermes Agent (6 files) to add NapCat support
- Write the NapCat OneBot 11 config
- Update `~/.hermes/config.yaml`
- Ask for your QQ number and admin list

To also download and install NapCat automatically:

```bash
hermes-napcat setup --with-napcat
```

Or non-interactively:

```bash
hermes-napcat setup \
  --qq 123456789 \
  --admins "123456789,987654321" \
  --with-napcat
```

### 3. Start NapCat and scan the QR code

```bash
hermes-napcat napcat start
screen -r napcat    # scan QR code here
# Ctrl+A then D to detach after login
```

### 4. Start Hermes Gateway

```bash
nohup hermes gateway run > /tmp/hermes-gateway.log 2>&1 &
```

---

## Manual Installation

If you prefer to patch Hermes manually:

```bash
hermes-napcat install                          # patch Hermes only
hermes-napcat install --hermes-dir /path/to/hermes-agent
hermes-napcat status                           # verify all patches applied
```

---

## Configuration

`~/.hermes/config.yaml`:

```yaml
platforms:
  napcat:
    enabled: true
    extra:
      http_api: "http://127.0.0.1:18801"   # NapCat HTTP API
      access_token: ""                      # Bearer token (if set in NapCat)
      self_id: "123456789"                  # Bot QQ number
      ws_port: 18800                        # Reverse WS listen port
      dm_policy: open                       # open | allowlist | disabled
      allow_from: []                        # QQ numbers allowed for DMs (allowlist mode)
      admins:                               # Can use management commands
        - "123456789"

platform_toolsets:
  napcat:
    - hermes-napcat

group_sessions_per_user: false              # Whole group shares one session
```

### NapCat onebot11 config

`~/Napcat/opt/QQ/resources/app/app_launcher/napcat/config/onebot11.json`:

```json
{
  "network": {
    "httpServers": [{
      "name": "httpServer",
      "enable": true,
      "port": 18801,
      "host": "0.0.0.0",
      "enableCors": true,
      "enableWebsocket": true,
      "messagePostFormat": "array",
      "token": "",
      "debug": false
    }],
    "websocketClients": [{
      "name": "HermesWs",
      "enable": true,
      "url": "ws://127.0.0.1:18800",
      "messagePostFormat": "array",
      "reportSelfMessage": false,
      "reconnectInterval": 5000,
      "token": "",
      "debug": false,
      "heartInterval": 30000
    }],
    "websocketServers": [],
    "httpSseServers": []
  }
}
```

---

## CLI Reference

```
hermes-napcat setup              Interactive setup wizard
hermes-napcat setup --with-napcat  Also install NapCat
hermes-napcat install            Patch Hermes Agent only
hermes-napcat uninstall          Remove patches + NapCat (default: both)
hermes-napcat uninstall --hermes-only   Remove Hermes patches only
hermes-napcat uninstall --napcat-only   Remove NapCat binary only
hermes-napcat status             Show installation status
hermes-napcat napcat start       Start NapCat (screen session)
hermes-napcat napcat stop        Stop NapCat
hermes-napcat napcat status      Show NapCat process status
hermes-napcat restart            Restart NapCat + Hermes Gateway
hermes-napcat systemd install    Create and enable systemd services
hermes-napcat systemd remove     Remove systemd services
```

---

## Admin System

Set `admins` in config to restrict management commands:

```yaml
admins:
  - "123456789"    # these QQ numbers can use management commands
```

If `admins` is empty, all users can call any tool (open mode).

**Admin-only tools:** kick, mute, set_admin, rename group, whole-group ban, leave group, set portrait, set special title, set/delete essence messages, publish/delete notices, delete group files, handle friend/group requests, delete friend.

---

## Available Tools

| Category | Tools |
|----------|-------|
| Messaging | `qq_send_message`, `qq_recall_message`, `qq_set_msg_emoji_like`, `qq_forward_message`, `qq_send_group_forward_msg`, `qq_send_private_forward_msg`, `qq_mark_msg_as_read` |
| History | `qq_get_group_msg_history`, `qq_get_friend_msg_history`, `qq_get_essence_msg_list`, `qq_set_essence_msg`, `qq_delete_essence_msg` |
| User & Friends | `qq_get_user_info`, `qq_get_friend_list`, `qq_like_user`, `qq_poke`, `qq_set_friend_remark`, `qq_delete_friend`, `qq_handle_friend_request` |
| Group Info | `qq_get_group_info`, `qq_get_group_list`, `qq_get_group_member_info`, `qq_get_group_member_list`, `qq_get_group_honor_info`, `qq_get_group_at_all_remain` |
| Group Management | `qq_mute_group_member`, `qq_kick_group_member`, `qq_set_group_admin`, `qq_set_group_name`, `qq_set_group_card`, `qq_set_group_whole_ban`, `qq_set_group_special_title`, `qq_leave_group`, `qq_set_group_sign`, `qq_set_group_remark`, `qq_set_group_portrait`, `qq_handle_group_request` |
| Notices | `qq_send_group_notice`, `qq_get_group_notice`, `qq_delete_group_notice` |
| Files | `qq_upload_file`, `qq_get_group_root_files`, `qq_get_group_file_url`, `qq_create_group_file_folder`, `qq_delete_group_file`, `qq_download_file` |
| Misc | `qq_ocr_image`, `qq_translate_en2zh` |

---

## How It Works

1. **NapCat** dials out to Hermes at `ws://127.0.0.1:18800` (reverse WebSocket)
2. **hermes-napcat adapter** receives the OneBot 11 event, extracts text/media, checks DM/group policy, prefixes sender name in group messages
3. **Hermes Agent** processes the message with full tool access
4. **Response** is sent back via NapCat's HTTP API at `http://127.0.0.1:18801`

### Session isolation

| Chat type | Session key |
|-----------|-------------|
| Private (DM) | One session per QQ user |
| Group (`group_sessions_per_user: false`) | One session per group |
| Group (`group_sessions_per_user: true`) | One session per user per group |

---

## Uninstall

```bash
# Remove everything (Hermes patches + NapCat binary)
hermes-napcat uninstall

# Keep NapCat, remove only Hermes patches
hermes-napcat uninstall --hermes-only

# Keep Hermes patches, remove only NapCat
hermes-napcat uninstall --napcat-only

# Keep QQ session data
hermes-napcat uninstall --keep-data
```

---

## Systemd (auto-start on reboot)

```bash
hermes-napcat systemd install    # creates napcat.service + hermes-gateway.service
hermes-napcat systemd remove
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bot not responding in group | Not @-mentioned | @机器人 in group messages |
| `ECONNREFUSED 127.0.0.1:18800` | Gateway not running | Start gateway: `hermes gateway run` |
| `403 unsupported_user_agent` | API provider blocks SDK user-agent | Patch `run_agent.py` — see [Notes for specific providers](#notes-for-specific-providers) |
| `KeyError: 'napcat'` | `platforms.py` not patched | Re-run `hermes-napcat install` |
| `Unauthorized user` on all messages | `run.py` auth bypass missing | Re-run `hermes-napcat install` |
| `Permission denied: only admins` | Sender not in admins list | Add QQ to `admins` in config, or set `admins: []` for open mode |
| NapCat QR code not refreshing | Screen session issue | `screen -r napcat` to reattach |

### Notes for specific providers

Some API providers block requests from the OpenAI SDK's default `AsyncOpenAI/Python X.X.X` user-agent. In `~/.hermes/hermes-agent/run_agent.py`, inside `_apply_client_headers_for_base_url`, add before the `else` branch:

```python
elif "your-provider.com" in normalized:
    self._client_kwargs["default_headers"] = {
        "User-Agent": "codex_cli_rs/0.0.0",
        "originator": "codex_cli_rs"
    }
```

Apply the same pattern in the second location (~line 1176) and in `agent/auxiliary_client.py`.

---

## License

MIT
