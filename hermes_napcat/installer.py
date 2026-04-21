"""Installer: patches a local Hermes Agent source tree to add NapCat support.

Strategy
--------
1. Locate the Hermes ``gateway`` package (importable or via --hermes-dir).
2. Copy ``adapter.py`` → ``{gateway}/platforms/napcat.py``.
3. Patch ``{gateway}/config.py``:  add ``NAPCAT = "napcat"`` to Platform enum.
4. Patch ``{gateway}/run.py``:     add NapCat branch to ``_create_adapter()``.
5. Patch ``toolsets.py`` (sibling of ``gateway/``): add napcat toolset & include
   it in ``hermes-gateway``.

All patched files are backed up as ``<file>.napcat.bak`` before modification.
Uninstall restores the backups and removes ``gateway/platforms/napcat.py``.
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
from pathlib import Path

# ── Locate Hermes ─────────────────────────────────────────────────────────────

def find_hermes_dir(hint: str | None = None) -> Path:
    """Return the directory that contains the ``gateway`` package."""
    if hint:
        p = Path(hint).resolve()
        if (p / "gateway" / "__init__.py").exists():
            return p
        if (p / "__init__.py").exists() and p.name == "gateway":
            return p.parent
        raise FileNotFoundError(f"Cannot find Hermes gateway package in: {hint}")

    # Try importable gateway
    spec = importlib.util.find_spec("gateway")
    if spec and spec.origin:
        return Path(spec.origin).parent.parent  # gateway/__init__.py → root

    # Try common install locations
    candidates = [
        Path.home() / ".hermes" / "hermes-agent",
        Path("/opt/hermes-agent"),
        Path("/usr/local/hermes-agent"),
    ]
    for p in candidates:
        if (p / "gateway" / "__init__.py").exists():
            return p

    raise FileNotFoundError(
        "Cannot locate Hermes Agent installation.\n"
        "Install it first:\n"
        "  git clone https://github.com/NousResearch/hermes-agent ~/.hermes/hermes-agent\n"
        "  cd ~/.hermes/hermes-agent && pip install -e . --break-system-packages\n"
        "Or specify the path: hermes-napcat setup --hermes-dir /path/to/hermes-agent"
    )


# ── File helpers ──────────────────────────────────────────────────────────────

def _backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".napcat.bak")
    if not bak.exists():
        shutil.copy2(path, bak)


def _restore(path: Path) -> bool:
    bak = path.with_suffix(path.suffix + ".napcat.bak")
    if bak.exists():
        shutil.copy2(bak, path)
        bak.unlink()
        return True
    return False


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ── Step 1: copy adapter ──────────────────────────────────────────────────────

def _install_adapter(hermes_root: Path) -> None:
    pkg = Path(__file__).parent
    platforms_dir = hermes_root / "gateway" / "platforms"
    tools_dir = hermes_root / "tools"

    # Copy adapter (napcat.py) — rewrites relative imports to absolute
    adapter_src = (pkg / "adapter.py").read_text(encoding="utf-8")
    adapter_src = adapter_src.replace(
        "from .api import",
        "from gateway.platforms.napcat_api import",
    )
    # After install, qq_tool lives in tools/, not gateway/platforms/
    adapter_src = adapter_src.replace(
        "from gateway.platforms import qq_tool as _qq_tool",
        "import tools.qq_tool as _qq_tool",
    )
    dst = platforms_dir / "napcat.py"
    dst.write_text(adapter_src, encoding="utf-8")
    print(f"  [+] Copied adapter        → {dst}")

    # Copy api module as napcat_api.py
    api_dst = platforms_dir / "napcat_api.py"
    shutil.copy2(pkg / "api.py", api_dst)
    print(f"  [+] Copied API client     → {api_dst}")

    # Copy qq_tool.py into tools/
    if tools_dir.exists():
        shutil.copy2(pkg / "qq_tool.py", tools_dir / "qq_tool.py")
        print(f"  [+] Copied QQ tools       → {tools_dir / 'qq_tool.py'}")
    else:
        print(f"  [!] tools/ directory not found — qq_tool.py not installed")


def _uninstall_adapter(hermes_root: Path) -> None:
    platforms_dir = hermes_root / "gateway" / "platforms"
    for name in ("napcat.py", "napcat_api.py"):
        p = platforms_dir / name
        if p.exists():
            p.unlink()
            print(f"  [-] Removed {p}")

    qq_tool = hermes_root / "tools" / "qq_tool.py"
    if qq_tool.exists():
        qq_tool.unlink()
        print(f"  [-] Removed {qq_tool}")


# ── Step 2: patch gateway/config.py ──────────────────────────────────────────

_CONFIG_MARKER = "# napcat-installed"
_NAPCAT_ENUM_LINE = '    NAPCAT = "napcat"  ' + _CONFIG_MARKER


def _patch_config(hermes_root: Path) -> None:
    path = hermes_root / "gateway" / "config.py"
    _backup(path)
    src = _read(path)

    if _CONFIG_MARKER in src:
        print("  [=] gateway/config.py already patched")
        return

    # Insert NAPCAT into the Platform enum after the last existing member
    # We look for the class definition and insert before the closing line
    pattern = r'(class Platform\(.*?Enum.*?\):.*?)(^\s*\w+ = "[^"]+"\s*$)'
    match = re.search(pattern, src, re.MULTILINE | re.DOTALL)
    if not match:
        # Fallback: find last quoted enum value and insert after it
        last = list(re.finditer(r'^    \w+ = "[^"]+"', src, re.MULTILINE))
        if not last:
            raise RuntimeError("Could not find Platform enum in gateway/config.py")
        pos = last[-1].end()
        src = src[:pos] + "\n" + _NAPCAT_ENUM_LINE + src[pos:]
    else:
        # Insert after the last member found by the full pattern scan
        last = list(re.finditer(r'^    \w+ = "[^"]+"', src, re.MULTILINE))
        pos = last[-1].end()
        src = src[:pos] + "\n" + _NAPCAT_ENUM_LINE + src[pos:]

    _write(path, src)
    print("  [+] Patched gateway/config.py (Platform.NAPCAT)")


def _unpatch_config(hermes_root: Path) -> None:
    path = hermes_root / "gateway" / "config.py"
    if _restore(path):
        print("  [-] Restored gateway/config.py")


# ── Step 3: patch gateway/run.py ─────────────────────────────────────────────

_RUN_MARKER = "# napcat-installed"


def _patch_run(hermes_root: Path) -> None:
    path = hermes_root / "gateway" / "run.py"
    _backup(path)
    src = _read(path)

    if _RUN_MARKER in src:
        print("  [=] gateway/run.py already patched")
        return

    # Locate _create_adapter function definition
    func_match = re.search(r'^([ \t]*)def _create_adapter\(', src, re.MULTILINE)
    if not func_match:
        raise RuntimeError("Could not find _create_adapter in gateway/run.py")
    func_pos = func_match.start()

    # Detect body indentation from the first elif/return inside the function
    body_match = re.search(r'\n([ \t]+)(elif|return)\s', src[func_pos:])
    body_indent = body_match.group(1) if body_match else "        "
    inner_indent = body_indent + "    "

    napcat_block = (
        f"\n{body_indent}elif platform == Platform.NAPCAT:  {_RUN_MARKER}\n"
        f"{inner_indent}from gateway.platforms.napcat import NapCatAdapter, check_napcat_requirements\n"
        f"{inner_indent}if not check_napcat_requirements():\n"
        f"{inner_indent}    logger.warning('NapCat: aiohttp not installed')\n"
        f"{inner_indent}    return None\n"
        f"{inner_indent}return NapCatAdapter(config)\n"
    )

    # Insert before the final "return None" inside _create_adapter
    return_match = re.search(
        r'(?m)^' + re.escape(body_indent) + r'return None\b',
        src[func_pos:],
    )
    if return_match:
        insert_pos = func_pos + return_match.start()
        src = src[:insert_pos] + napcat_block + src[insert_pos:]
    else:
        # Fallback: insert after the last elif at body indent level
        last_elif = list(re.finditer(
            r'(?m)^' + re.escape(body_indent) + r'elif platform == Platform\.\w+:',
            src[func_pos:],
        ))
        if not last_elif:
            raise RuntimeError("Could not find adapter dispatch in gateway/run.py")
        pos = func_pos + last_elif[-1].start()
        next_block = re.search(
            r'\n' + re.escape(body_indent) + r'(elif|else|return)', src[pos:]
        )
        insert_pos = pos + next_block.start(0) + 1 if next_block else len(src)
        src = src[:insert_pos] + napcat_block + src[insert_pos:]

    _write(path, src)
    print("  [+] Patched gateway/run.py (_create_adapter)")


def _unpatch_run(hermes_root: Path) -> None:
    path = hermes_root / "gateway" / "run.py"
    if _restore(path):
        print("  [-] Restored gateway/run.py")


# ── Step 4: patch toolsets.py ────────────────────────────────────────────────

_TOOLSETS_MARKER = "# napcat-installed"
_NAPCAT_TOOLSET_BLOCK = (
    '\n    "hermes-napcat": {  ' + _TOOLSETS_MARKER + '\n'
    '        "description": "QQ (NapCat / OneBot 11) toolset — group management, messaging, files",\n'
    '        "tools": [\n'
    '            "qq_like_user", "qq_get_user_info", "qq_get_group_info",\n'
    '            "qq_get_group_member_info", "qq_mute_group_member", "qq_kick_group_member",\n'
    '            "qq_poke", "qq_recall_message", "qq_set_group_card", "qq_get_friend_list",\n'
    '            "qq_get_group_list", "qq_get_group_member_list", "qq_set_group_admin",\n'
    '            "qq_set_group_name", "qq_set_group_whole_ban", "qq_send_group_notice",\n'
    '            "qq_get_group_honor_info", "qq_send_message", "qq_upload_file",\n'
    '            "qq_forward_message", "qq_set_group_special_title", "qq_leave_group",\n'
    '            "qq_handle_friend_request", "qq_handle_group_request",\n'
    '            "qq_get_group_msg_history", "qq_get_friend_msg_history",\n'
    '            "qq_get_essence_msg_list", "qq_set_essence_msg", "qq_delete_essence_msg",\n'
    '            "qq_set_msg_emoji_like", "qq_ocr_image", "qq_set_friend_remark",\n'
    '            "qq_delete_friend", "qq_get_group_root_files", "qq_get_group_file_url",\n'
    '            "qq_create_group_file_folder", "qq_delete_group_file",\n'
    '            "qq_get_group_notice", "qq_delete_group_notice", "qq_set_group_portrait",\n'
    '            "qq_send_group_forward_msg", "qq_send_private_forward_msg",\n'
    '            "qq_mark_msg_as_read", "qq_get_group_at_all_remain",\n'
    '            "qq_translate_en2zh", "qq_download_file", "qq_set_group_sign",\n'
    '            "qq_set_group_remark",\n'
    '        ],\n'
    '        "includes": [],\n'
    '    },\n'
)


def _patch_toolsets(hermes_root: Path) -> None:
    path = hermes_root / "toolsets.py"
    if not path.exists():
        print("  [!] toolsets.py not found — skipping toolset registration")
        return
    _backup(path)
    src = _read(path)

    if _TOOLSETS_MARKER in src:
        print("  [=] toolsets.py already patched")
        return

    # Add "hermes-napcat" to hermes-gateway includes list
    def _add_to_gateway_includes(text: str) -> str:
        pattern = r'("hermes-gateway".*?"includes"\s*:\s*\[)(.*?)(\])'
        m = re.search(pattern, text, re.DOTALL)
        if m:
            includes_content = m.group(2)
            if '"hermes-napcat"' not in includes_content:
                # Ensure last item ends with a comma before appending
                trimmed = includes_content.rstrip()
                if trimmed and not trimmed.endswith(','):
                    trimmed += ','
                new_includes = trimmed + '\n        "hermes-napcat",  ' + _TOOLSETS_MARKER + "\n    "
                text = text[:m.start(2)] + new_includes + text[m.end(2):]
        return text

    # Insert the napcat toolset block before the last closing brace of TOOLSETS.
    # The block already ends with '},\n' so the dict entry is properly terminated.
    last_brace = src.rfind("\n}")
    if last_brace == -1:
        print("  [!] Cannot locate TOOLSETS dict end — skipping")
        return

    # Ensure the entry just before the insertion point ends with a comma.
    before = src[:last_brace].rstrip()
    if before and not before.endswith(','):
        src = before + ',\n' + _NAPCAT_TOOLSET_BLOCK + src[last_brace:]
    else:
        src = src[:last_brace] + _NAPCAT_TOOLSET_BLOCK + src[last_brace:]
    src = _add_to_gateway_includes(src)

    _write(path, src)
    print("  [+] Patched toolsets.py (hermes-napcat toolset)")


def _unpatch_toolsets(hermes_root: Path) -> None:
    path = hermes_root / "toolsets.py"
    if path.exists() and _restore(path):
        print("  [-] Restored toolsets.py")


# ── Step 5: patch hermes_cli/platforms.py ────────────────────────────────────

_PLATFORMS_MARKER = "# napcat-installed"
_NAPCAT_PLATFORMS_LINE = (
    '    ("napcat",         PlatformInfo(label="🐧 NapCat (QQ)",     default_toolset="hermes-napcat")),  '
    + _PLATFORMS_MARKER
)


def _patch_platforms(hermes_root: Path) -> None:
    path = hermes_root / "hermes_cli" / "platforms.py"
    if not path.exists():
        print("  [!] hermes_cli/platforms.py not found — skipping")
        return
    _backup(path)
    src = _read(path)

    if _PLATFORMS_MARKER in src:
        print("  [=] hermes_cli/platforms.py already patched")
        return

    # Insert napcat entry before the webhook entry
    target = '    ("webhook",'
    if target in src:
        src = src.replace(target, _NAPCAT_PLATFORMS_LINE + "\n" + target)
    else:
        # Fallback: insert after the last PlatformInfo line
        last = list(re.finditer(r'^    \("[^"]+",\s+PlatformInfo', src, re.MULTILINE))
        if not last:
            raise RuntimeError("Cannot find PLATFORMS list in hermes_cli/platforms.py")
        eol = src.index("\n", last[-1].end())
        src = src[:eol + 1] + _NAPCAT_PLATFORMS_LINE + "\n" + src[eol + 1:]

    _write(path, src)
    print("  [+] Patched hermes_cli/platforms.py (napcat platform entry)")


def _unpatch_platforms(hermes_root: Path) -> None:
    path = hermes_root / "hermes_cli" / "platforms.py"
    if path.exists() and _restore(path):
        print("  [-] Restored hermes_cli/platforms.py")


# ── Step 6: patch gateway/run.py _is_user_authorized ─────────────────────────

_RUN_AUTH_MARKER = "# napcat-installed-auth"
_RUN_AUTH_TARGET = "if source.platform in (Platform.HOMEASSISTANT, Platform.WEBHOOK):"
_RUN_AUTH_REPLACEMENT = (
    "if source.platform in (Platform.HOMEASSISTANT, Platform.WEBHOOK, Platform.NAPCAT):  "
    + _RUN_AUTH_MARKER
)


def _patch_run_auth(hermes_root: Path) -> None:
    path = hermes_root / "gateway" / "run.py"
    src = _read(path)

    if _RUN_AUTH_MARKER in src:
        print("  [=] gateway/run.py auth bypass already patched")
        return

    if _RUN_AUTH_TARGET not in src:
        print("  [!] gateway/run.py: auth check pattern not found — skipping")
        return

    # _backup is a no-op if run.py.napcat.bak already exists from _patch_run
    _backup(path)
    src = src.replace(_RUN_AUTH_TARGET, _RUN_AUTH_REPLACEMENT, 1)
    _write(path, src)
    print("  [+] Patched gateway/run.py (NapCat auth bypass)")


def _unpatch_run_auth(hermes_root: Path) -> None:
    path = hermes_root / "gateway" / "run.py"
    src = _read(path)
    if _RUN_AUTH_MARKER not in src:
        return
    src = src.replace(_RUN_AUTH_REPLACEMENT, _RUN_AUTH_TARGET, 1)
    _write(path, src)
    print("  [-] Removed NapCat auth bypass from gateway/run.py")


# ── Step 7: install skill file ────────────────────────────────────────────────

def _install_skill(hermes_root: Path) -> None:
    skill_src = Path(__file__).parent / "skills" / "qq" / "SKILL.md"
    if not skill_src.exists():
        print("  [!] skills/qq/SKILL.md not found in package — skipping")
        return
    dst_dir = hermes_root / "skills" / "qq"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "SKILL.md"
    shutil.copy2(skill_src, dst)
    print(f"  [+] Installed skill       → {dst}")


def _uninstall_skill(hermes_root: Path) -> None:
    dst = hermes_root / "skills" / "qq" / "SKILL.md"
    if dst.exists():
        dst.unlink()
        print(f"  [-] Removed skill ({dst})")
    parent = dst.parent
    if parent.exists() and not any(parent.iterdir()):
        parent.rmdir()


# ── Public API ────────────────────────────────────────────────────────────────

def install(hermes_dir: str | None = None) -> None:
    root = find_hermes_dir(hermes_dir)
    print(f"\nInstalling hermes-napcat into: {root}\n")
    _install_adapter(root)
    _patch_config(root)
    _patch_run(root)
    _patch_toolsets(root)
    _patch_platforms(root)
    _patch_run_auth(root)
    _install_skill(root)
    print("\n✓ Installation complete.\n")
    print("Add the following to ~/.hermes/config.yaml:\n")
    print("  platforms:")
    print("    napcat:")
    print("      enabled: true")
    print("      extras:")
    print('        http_api: "http://127.0.0.1:18801"')
    print('        access_token: ""')
    print('        self_id: "YOUR_QQ_NUMBER"')
    print("        ws_port: 18800")
    print('        dm_policy: "allowlist"')
    print("        allow_from: []")
    print("        admins: []")
    print()
    print("Configure NapCat reverse WebSocket:")
    print('  { "reverseWebSocket": [{ "url": "ws://127.0.0.1:18800" }] }')
    print()


def uninstall(hermes_dir: str | None = None) -> None:
    root = find_hermes_dir(hermes_dir)
    print(f"\nUninstalling hermes-napcat from: {root}\n")
    _uninstall_adapter(root)
    _unpatch_config(root)
    _unpatch_run(root)
    _unpatch_toolsets(root)
    _unpatch_platforms(root)
    _unpatch_run_auth(root)
    _uninstall_skill(root)
    print("\n✓ Uninstall complete.\n")


def status(hermes_dir: str | None = None) -> None:
    root = find_hermes_dir(hermes_dir)
    adapter = root / "gateway" / "platforms" / "napcat.py"
    qq_tool = root / "tools" / "qq_tool.py"
    config_patched = _CONFIG_MARKER in _read(root / "gateway" / "config.py")
    run_patched = _RUN_MARKER in _read(root / "gateway" / "run.py")
    ts_path = root / "toolsets.py"
    toolsets_patched = _TOOLSETS_MARKER in _read(ts_path) if ts_path.exists() else False

    platforms_path = root / "hermes_cli" / "platforms.py"
    platforms_patched = (
        _PLATFORMS_MARKER in _read(platforms_path)
        if platforms_path.exists() else False
    )
    run_src = _read(root / "gateway" / "run.py")
    run_auth_patched = _RUN_AUTH_MARKER in run_src
    skill_installed = (root / "skills" / "qq" / "SKILL.md").exists()

    print(f"\nhermes-napcat status in: {root}")
    print(f"  adapter file:   {'✓' if adapter.exists() else '✗'}")
    print(f"  qq_tool file:   {'✓' if qq_tool.exists() else '✗'}")
    print(f"  config.py:      {'✓' if config_patched else '✗'}")
    print(f"  run.py:         {'✓' if run_patched else '✗'}")
    print(f"  toolsets.py:    {'✓' if toolsets_patched else '✗ (optional)'}")
    print(f"  platforms.py:   {'✓' if platforms_patched else '✗'}")
    print(f"  run.py auth:    {'✓' if run_auth_patched else '✗'}")
    print(f"  skill (qq):     {'✓' if skill_installed else '✗'}")
    all_ok = (adapter.exists() and qq_tool.exists() and config_patched
              and run_patched and platforms_patched and run_auth_patched
              and skill_installed)
    print(f"\n  {'Fully installed' if all_ok else 'Not fully installed'}")
    print()
