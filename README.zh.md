<div align="center">

# hermes-napcat

**[Hermes Agent](https://github.com/NousResearch/hermes-agent) 的 NapCat（QQ / OneBot 11）平台适配器**

[![PyPI](https://img.shields.io/pypi/v/hermes-napcat?color=blue)](https://pypi.org/project/hermes-napcat/)
[![Python](https://img.shields.io/pypi/pyversions/hermes-napcat)](https://pypi.org/project/hermes-napcat/)
[![License](https://img.shields.io/github/license/shubyi/hermes-napcat)](LICENSE)

[English](README.md) · [中文](README.zh.md)

</div>

通过 [NapCat](https://github.com/NapNeko/NapCatQQ) 的 OneBot 11 反向 WebSocket 将 Hermes 接入 QQ。在任意 QQ 群或私聊中与 AI 助手对话，支持完整的群管理功能和管理员权限控制。

```
QQ客户端 ──── NapCat ──WS──▶ hermes-napcat ──▶ Hermes（大模型）
                                  │                    │
                                  └─────HTTP API ◀─────┘
                                 （18801端口）  （18800端口）
```

---

## 功能特性

- **群聊 & 私聊** — 群聊 @机器人，私聊直接发消息
- **群共享会话** — 整个群共用一个上下文，消息自动带发送者昵称前缀
- **管理员系统** — 限制 QQ 管理指令（禁言、踢人等）只有指定 QQ 才能使用
- **48 个 QQ 工具** — 消息、群管理、文件操作、OCR、表情回应等一应俱全
- **多媒体支持** — 图片、语音（ffmpeg 转 WAV）、视频、文件上传下载
- **引用消息上下文** — 回复消息时自动携带被引用内容
- **一键安装向导** — 交互式向导自动完成安装和配置

---

## 环境要求

- Python 3.11+
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)（源码安装）
- [NapCat](https://github.com/NapNeko/NapCatQQ)（需开启 HTTP API + 反向 WS）
- `aiohttp >= 3.9`
- `ffmpeg` *（可选，用于语音消息转录）*

---

## 快速开始

### 1. 安装

```bash
pip install hermes-napcat
```

### 2. 运行安装向导

```bash
hermes-napcat setup
```

向导会自动修补 Hermes Agent、写入 NapCat 配置、更新 `~/.hermes/config.yaml`，并询问你的 QQ 号和管理员列表。

同时自动下载安装 NapCat：

```bash
hermes-napcat setup --with-napcat
```

非交互式安装（脚本/CI 环境）：

```bash
hermes-napcat setup --qq 123456789 --admins "123456789,987654321" --with-napcat
```

### 3. 启动 NapCat

```bash
hermes-napcat napcat start
```

二维码直接打印在终端，用 QQ 扫码登录。再次启动时自动从缓存 session 登录，无需重新扫码。

### 4. 启动 Hermes 网关

```bash
nohup hermes gateway run > /tmp/hermes-gateway.log 2>&1 &
```

---

## 配置说明

`~/.hermes/config.yaml`：

```yaml
platforms:
  napcat:
    enabled: true
    extra:
      http_api: "http://127.0.0.1:18801"   # NapCat HTTP API 地址
      access_token: ""                      # Bearer Token（NapCat 中设置后填写）
      self_id: "123456789"                  # 机器人 QQ 号
      ws_port: 18800                        # 反向 WS 监听端口
      dm_policy: open                       # open（开放）| allowlist（白名单）| disabled（关闭）
      allow_from: []                        # 允许私聊的 QQ 号（白名单模式）
      admins:                               # 可使用管理指令的 QQ 号
        - "123456789"

platform_toolsets:
  napcat:
    - hermes-cli
    - hermes-napcat

group_sessions_per_user: false              # 整个群共享一个会话
```

### NapCat OneBot 11 配置

`~/Napcat/opt/QQ/resources/app/app_launcher/napcat/config/onebot11.json`：

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

## 管理员系统

在配置中设置 `admins` 来限制谁可以使用管理指令：

```yaml
admins:
  - "123456789"
```

若 `admins` 为空，则所有人均可调用任意工具（开放模式）。

### 权限级别

| 操作 | 普通用户 | 管理员 |
|------|:-------:|:------:|
| 搜索、查询、写代码、读文件等常规功能 | ✅ | ✅ |
| QQ 管理工具（禁言、踢人、设置管理员等） | ❌ | ✅ |
| 破坏性系统操作 | ❌ | ⚠️ 需二次确认 |

管理员请求不可逆操作时，机器人会先说明操作内容，等待确认后再执行。

**仅管理员可用的 QQ 工具：** 踢人、禁言、设置管理员、修改群名、全群禁言、退群、设置群头像、设置专属头衔、设置/删除精华消息、发布/删除群公告、删除群文件、处理加好友/加群请求、删除好友。

---

## 可用工具

| 分类 | 工具 |
|------|------|
| 消息 | `qq_send_message`、`qq_recall_message`、`qq_set_msg_emoji_like`、`qq_forward_message`、`qq_send_group_forward_msg`、`qq_send_private_forward_msg`、`qq_mark_msg_as_read` |
| 历史记录 | `qq_get_group_msg_history`、`qq_get_friend_msg_history`、`qq_get_essence_msg_list`、`qq_set_essence_msg`、`qq_delete_essence_msg` |
| 用户 & 好友 | `qq_get_user_info`、`qq_get_friend_list`、`qq_like_user`、`qq_poke`、`qq_set_friend_remark`、`qq_delete_friend`、`qq_handle_friend_request` |
| 群信息 | `qq_get_group_info`、`qq_get_group_list`、`qq_get_group_member_info`、`qq_get_group_member_list`、`qq_get_group_honor_info`、`qq_get_group_at_all_remain` |
| 群管理 | `qq_mute_group_member`、`qq_kick_group_member`、`qq_set_group_admin`、`qq_set_group_name`、`qq_set_group_card`、`qq_set_group_whole_ban`、`qq_set_group_special_title`、`qq_leave_group`、`qq_set_group_sign`、`qq_set_group_remark`、`qq_set_group_portrait`、`qq_handle_group_request` |
| 群公告 | `qq_send_group_notice`、`qq_get_group_notice`、`qq_delete_group_notice` |
| 文件 | `qq_upload_file`、`qq_get_group_root_files`、`qq_get_group_file_url`、`qq_create_group_file_folder`、`qq_delete_group_file`、`qq_download_file` |
| 其他 | `qq_ocr_image`、`qq_translate_en2zh` |

---

## 工作原理

1. **NapCat** 主动连接到 `ws://127.0.0.1:18800`（反向 WebSocket）
2. **hermes-napcat** 接收 OneBot 11 事件，提取文字/媒体，检查私聊/群聊策略，群消息自动加发送者昵称前缀
3. **Hermes Agent** 使用完整工具集处理消息
4. **响应结果** 通过 NapCat 的 HTTP API（`http://127.0.0.1:18801`）发回

### 会话隔离策略

| 聊天类型 | 会话键 |
|----------|--------|
| 私聊（DM） | 每个 QQ 号独立会话 |
| 群聊（`group_sessions_per_user: false`） | 整个群共享一个会话 |
| 群聊（`group_sessions_per_user: true`） | 每人在每个群各自独立会话 |

---

## CLI 命令参考

| 命令 | 说明 |
|------|------|
| `hermes-napcat setup` | 交互式安装向导 |
| `hermes-napcat setup --with-napcat` | 同时安装 NapCat |
| `hermes-napcat install` | 仅修补 Hermes Agent |
| `hermes-napcat uninstall` | 移除所有内容（默认：补丁 + NapCat） |
| `hermes-napcat uninstall --hermes-only` | 仅移除 Hermes 补丁 |
| `hermes-napcat uninstall --napcat-only` | 仅移除 NapCat 二进制 |
| `hermes-napcat status` | 查看安装状态 |
| `hermes-napcat napcat start` | 启动 NapCat（screen 会话） |
| `hermes-napcat napcat stop` | 停止 NapCat |
| `hermes-napcat napcat status` | 查看 NapCat 进程状态 |
| `hermes-napcat restart` | 重启 NapCat + Hermes 网关 |
| `hermes-napcat systemd install` | 创建并启用 systemd 服务 |
| `hermes-napcat systemd remove` | 移除 systemd 服务 |

---

## 卸载

```bash
hermes-napcat uninstall                  # 移除所有内容
hermes-napcat uninstall --hermes-only    # 保留 NapCat，仅移除 Hermes 补丁
hermes-napcat uninstall --napcat-only    # 保留 Hermes 补丁，仅移除 NapCat
hermes-napcat uninstall --keep-data      # 保留 QQ 会话数据
```

---

## Systemd 服务（开机自启）

```bash
hermes-napcat systemd install    # 创建 napcat.service + hermes-gateway.service
hermes-napcat systemd remove
```

---

## 常见问题排查

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| 群里不回消息 | 未被 @ | 在群消息中 @机器人 |
| `ECONNREFUSED 127.0.0.1:18800` | 网关未运行 | `hermes gateway run` |
| `403 unsupported_user_agent` | API 提供商拦截了 SDK 的 User-Agent | 参见下方说明 |
| `KeyError: 'napcat'` | `platforms.py` 未打补丁 | 重新运行 `hermes-napcat install` |
| 所有消息均提示 `Unauthorized user` | `run.py` 缺少认证绕过 | 重新运行 `hermes-napcat install` |
| `Permission denied: only admins` | 发送者不在管理员列表 | 将 QQ 号加入 `admins`，或设置 `admins: []` |
| NapCat 二维码未显示 | 启动超时 | `tail -f /tmp/napcat.log` 或 `screen -r napcat` |

### 特定 API 提供商说明

部分 API 提供商会拦截 OpenAI SDK 默认的 `AsyncOpenAI/Python X.X.X` User-Agent。在 `~/.hermes/hermes-agent/run_agent.py` 的 `_apply_client_headers_for_base_url` 方法中，在 `else` 分支前加入：

```python
elif "your-provider.com" in normalized:
    self._client_kwargs["default_headers"] = {
        "User-Agent": "codex_cli_rs/0.0.0",
        "originator": "codex_cli_rs"
    }
```

同样的修改也需要应用到第二处位置（约第 1176 行）以及 `agent/auxiliary_client.py`。

---

## 贡献者

<!-- ALL-CONTRIBUTORS-LIST:START -->
| 头像 | 名字 | 角色 |
|------|------|------|
| [![shubyi](https://github.com/shubyi.png?size=60)](https://github.com/shubyi) | **[shubyi](https://github.com/shubyi)** | 创建者 & 维护者 |
<!-- ALL-CONTRIBUTORS-LIST:END -->

---

## 许可证

MIT
