"""NapCat installation and process management."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

# NapCat installer (official rootless Shell installer)
_INSTALLER_URL = "https://nclatest.znin.net/NapNeko/NapCat-Installer/main/script/install.sh"
_SCREEN_SESSION = "napcat"


def _pip_install(package: str) -> None:
    """Install a package via pip, auto-retrying with --break-system-packages on Debian."""
    cmd = [sys.executable, "-m", "pip", "install", package, "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return
    if "externally-managed-environment" in result.stderr or "externally managed" in result.stderr:
        subprocess.run(cmd + ["--break-system-packages"], check=True)
    else:
        raise RuntimeError(f"pip install {package} failed:\n{result.stderr}")


# ── Paths ──────────────────────────────────────────────────────────────────────

def napcat_home() -> Path:
    return Path.home() / "Napcat"


def qq_bin() -> Path:
    return napcat_home() / "opt" / "QQ" / "qq"


def napcat_config_dir() -> Path:
    return napcat_home() / "opt" / "QQ" / "resources" / "app" / "app_launcher" / "napcat" / "config"


def onebot_config_path(qq: str | None = None) -> Path:
    d = napcat_config_dir()
    if qq:
        return d / f"onebot11_{qq}.json"
    # v4.5.3+ default config
    return d / "onebot11.json"


# ── NapCat config ──────────────────────────────────────────────────────────────

def build_napcat_config(
    ws_port: int = 18800,
    http_port: int = 18801,
    access_token: str = "",
) -> dict:
    """Build the onebot11 network config dict."""
    return {
        "network": {
            "httpServers": [
                {
                    "name": "httpServer",
                    "enable": True,
                    "port": http_port,
                    "host": "0.0.0.0",
                    "enableCors": True,
                    "enableWebsocket": True,
                    "messagePostFormat": "array",
                    "token": access_token,
                    "debug": False,
                }
            ],
            "websocketClients": [
                {
                    "name": "HermesWs",
                    "enable": True,
                    "url": f"ws://127.0.0.1:{ws_port}",
                    "messagePostFormat": "array",
                    "reportSelfMessage": False,
                    "reconnectInterval": 5000,
                    "token": access_token,
                    "debug": False,
                    "heartInterval": 30000,
                }
            ],
            "websocketServers": [],
            "httpSseServers": [],
        },
        "musicSignUrl": "",
        "enableLocalFile2Url": False,
        "parseMultMsg": False,
    }


def write_napcat_config(
    qq: str | None,
    ws_port: int = 18800,
    http_port: int = 18801,
    access_token: str = "",
) -> Path:
    """Write NapCat onebot config. Returns the config file path."""
    cfg_dir = napcat_config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)

    cfg = build_napcat_config(ws_port, http_port, access_token)
    path = onebot_config_path(qq)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    # Also write the default config so it works before first login
    default = onebot_config_path(None)
    if not default.exists() or qq:
        default.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    return path


# ── Installer ──────────────────────────────────────────────────────────────────

def is_napcat_installed() -> bool:
    return qq_bin().exists()


def install_napcat() -> None:
    """Download and run the official NapCat Shell installer (rootless)."""
    if not shutil.which("curl") and not shutil.which("wget"):
        raise RuntimeError("curl or wget is required to download the NapCat installer.")

    print("  Downloading NapCat installer...")
    fd, script_path = tempfile.mkstemp(suffix=".sh")
    os.close(fd)

    try:
        urllib.request.urlretrieve(_INSTALLER_URL, script_path)
        os.chmod(script_path, 0o755)
    except Exception as exc:
        raise RuntimeError(f"Failed to download installer: {exc}") from exc

    print("  Running NapCat installer (rootless, no Docker)...\n")
    try:
        # --docker n = no Docker, --cli y = install TUI-CLI tool
        # cwd=home so installer creates ~/NapCat not ./NapCat
        subprocess.run(
            ["bash", script_path, "--docker", "n", "--cli", "y"],
            check=True,
            cwd=str(Path.home()),
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"NapCat installer failed: {exc}") from exc
    finally:
        os.unlink(script_path)


# ── Process management ─────────────────────────────────────────────────────────

def _screen_available() -> bool:
    return shutil.which("screen") is not None


def _xvfb_available() -> bool:
    return shutil.which("xvfb-run") is not None


def _napcat_has_session() -> bool:
    """True if QQ has cached session data — enables auto-login via -q flag."""
    config_dir = Path.home() / ".config" / "QQ"
    if not config_dir.exists():
        return False
    return any(config_dir.glob("nt_qq_*/nt_db/*.db"))


def _load_napcat_qq() -> str | None:
    """Read self_id from ~/.hermes/config.yaml (set after first login)."""
    try:
        import yaml
        p = _hermes_config_path()
        if not p.exists():
            return None
        with p.open() as f:
            cfg = yaml.safe_load(f) or {}
        qq = cfg.get("platforms", {}).get("napcat", {}).get("extra", {}).get("self_id")
        return str(qq) if qq and str(qq) not in ("", "YOUR_QQ_NUMBER") else None
    except Exception:
        return None


def _build_start_cmd(qq: str | None = None) -> str:
    qq_arg = f" -q {qq}" if qq else ""
    xvfb = "xvfb-run -a " if _xvfb_available() else ""
    return f'{xvfb}{qq_bin()} --no-sandbox{qq_arg}'


def _start_hermes_gateway() -> None:
    """Start Hermes gateway in the background if not already running."""
    hermes = shutil.which("hermes")
    if not hermes:
        print("  (hermes command not found — start gateway manually: hermes gateway run)")
        return
    result = subprocess.run([hermes, "gateway", "status"], capture_output=True, text=True)
    if "active (running)" in result.stdout or "running" in result.stdout.lower():
        print("✓ Hermes 网关已在运行")
        return
    log = Path(tempfile.gettempdir()) / "hermes-gateway.log"
    subprocess.Popen(
        [hermes, "gateway", "run", "--replace"],
        stdout=open(log, "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(f"✓ Hermes 网关已启动（日志 → {log}）")


def start_napcat(qq: str | None = None) -> None:
    """Start NapCat.

    - If session data exists → silent background start (no QR needed).
    - Otherwise → QR code is printed directly in this terminal; wait for login.
    """
    if not is_napcat_installed():
        print("NapCat is not installed.")
        if sys.stdin.isatty():
            ans = input("  Install NapCat now? (yes/no) [yes]: ").strip().lower() or "yes"
            if ans in ("yes", "y"):
                install_napcat()
            else:
                print("Aborted. Run: hermes-napcat setup --with-napcat")
                return
        else:
            raise RuntimeError("NapCat is not installed. Run: hermes-napcat setup --with-napcat")

    if not _screen_available():
        raise RuntimeError(
            "screen is not installed. Install it with:\n"
            "  apt install screen   (Debian/Ubuntu)\n"
            "  yum install screen   (CentOS/RHEL)"
        )

    if napcat_running():
        print("NapCat is already running.")
        return

    qq_to_use = qq or _load_napcat_qq()
    log_file = Path(tempfile.gettempdir()) / "napcat.log"

    if qq_to_use and _napcat_has_session():
        # Session cached → auto-login, no QR needed
        cmd = _build_start_cmd(qq_to_use) + f" 2>&1 | tee {log_file}"
        subprocess.run(["screen", "-dmS", _SCREEN_SESSION, "bash", "-c", cmd], check=True)
        print(f"✓ NapCat 已启动（自动登录 {qq_to_use}）")
        print(f"  日志 → {log_file}  |  附加：screen -r {_SCREEN_SESSION}")
        _start_hermes_gateway()
        return

    # No session → need QR code; stream output directly to this terminal
    import time
    try:
        log_file.unlink()
    except FileNotFoundError:
        pass

    cmd = _build_start_cmd(qq_to_use) + f" 2>&1 | tee {log_file}"
    subprocess.run(["screen", "-dmS", _SCREEN_SESSION, "bash", "-c", cmd], check=True)

    print("  正在启动 NapCat，等待二维码...", flush=True)
    deadline = time.time() + 90
    qr_shown = False
    logged_in = False
    last_pos = 0

    while time.time() < deadline:
        time.sleep(0.5)
        if not log_file.exists():
            continue
        try:
            content = log_file.read_text(errors="replace")
        except OSError:
            continue

        if not qr_shown and "█" in content:
            lines = content.splitlines()
            in_qr = False
            for line in lines:
                if "█" in line:
                    in_qr = True
                if in_qr:
                    print(line)
                if in_qr and "█" not in line and line.strip():
                    break
            qr_shown = True
            print("\n  ↑ 用 QQ 扫码登录，等待成功...", flush=True)
            last_pos = len(content)

        if "适配器初始化完成" in content:
            logged_in = True
            break

    if logged_in:
        print(f"\n✓ NapCat 登录成功，已在后台运行（日志 → {log_file}）")
        _start_hermes_gateway()
    elif qr_shown:
        print(f"\n  NapCat 仍在运行，扫码后会自动连接。日志 → {log_file}")
    else:
        print(f"\n  未检测到二维码，请检查日志：tail -f {log_file}")
        print(f"  或附加 screen：screen -r {_SCREEN_SESSION}")


def stop_napcat() -> None:
    """Stop the NapCat screen session."""
    if not napcat_running():
        print("NapCat is not running.")
        return
    subprocess.run(["screen", "-S", _SCREEN_SESSION, "-X", "quit"], check=False)
    print(f"✓ NapCat stopped (screen session '{_SCREEN_SESSION}' closed)")


def napcat_running() -> bool:
    """Return True if the NapCat screen session exists."""
    if not _screen_available():
        return False
    result = subprocess.run(
        ["screen", "-ls", _SCREEN_SESSION],
        capture_output=True, text=True,
    )
    return _SCREEN_SESSION in result.stdout


def _find_hermes_python() -> str:
    """Find the Python interpreter used by Hermes Agent."""
    candidates = [
        Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python",
        Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python3",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return shutil.which("python3") or "python3"


def uninstall_napcat(remove_data: bool = True) -> None:
    """Stop NapCat and remove its installation."""
    if napcat_running():
        stop_napcat()
        import time; time.sleep(1)

    home = napcat_home()
    if home.exists():
        shutil.rmtree(str(home))
        print(f"  [-] Removed NapCat installation ({home})")
    else:
        print("  [=] NapCat not installed, nothing to remove.")

    if remove_data:
        qq_config = Path.home() / ".config" / "QQ"
        if qq_config.exists():
            shutil.rmtree(str(qq_config))
            print(f"  [-] Removed QQ session data ({qq_config})")


_NAPCAT_SERVICE_NAME = "napcat"
_GATEWAY_SERVICE_NAME = "hermes-gateway"


def _systemd_path(name: str) -> Path:
    return Path(f"/etc/systemd/system/{name}.service")


def install_systemd(qq: str | None = None) -> None:
    """Create and enable systemd service files for NapCat and Hermes Gateway."""
    if not shutil.which("systemctl"):
        raise RuntimeError("systemd is not available on this system.")

    qq = qq or _get_qq_from_config()
    xvfb = "xvfb-run -a " if _xvfb_available() else ""
    qq_arg = f" -q {qq}" if qq else ""
    napcat_exec = f"{xvfb}{qq_bin()} --no-sandbox{qq_arg}"
    hermes_dir = Path.home() / ".hermes" / "hermes-agent"
    python = _find_hermes_python()

    napcat_unit = f"""\
[Unit]
Description=NapCat QQ Bot
After=network.target

[Service]
Type=simple
User=root
ExecStart={napcat_exec}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    gateway_unit = f"""\
[Unit]
Description=Hermes Gateway
After=network.target {_NAPCAT_SERVICE_NAME}.service

[Service]
Type=simple
User=root
WorkingDirectory={hermes_dir}
ExecStart={python} -m hermes_cli.main gateway run
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    _systemd_path(_NAPCAT_SERVICE_NAME).write_text(napcat_unit)
    print(f"  [+] Written {_systemd_path(_NAPCAT_SERVICE_NAME)}")
    _systemd_path(_GATEWAY_SERVICE_NAME).write_text(gateway_unit)
    print(f"  [+] Written {_systemd_path(_GATEWAY_SERVICE_NAME)}")

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", _NAPCAT_SERVICE_NAME, _GATEWAY_SERVICE_NAME], check=True)
    print(f"\n✓ Systemd services installed and enabled.")
    print(f"  Start:   systemctl start {_NAPCAT_SERVICE_NAME} {_GATEWAY_SERVICE_NAME}")
    print(f"  Status:  systemctl status {_NAPCAT_SERVICE_NAME} {_GATEWAY_SERVICE_NAME}")
    print(f"  Logs:    journalctl -u {_NAPCAT_SERVICE_NAME} -f")


def remove_systemd() -> None:
    """Stop, disable and remove the systemd service files."""
    if not shutil.which("systemctl"):
        print("  systemd not available.")
        return
    for name in (_NAPCAT_SERVICE_NAME, _GATEWAY_SERVICE_NAME):
        subprocess.run(["systemctl", "stop", name], check=False, capture_output=True)
        subprocess.run(["systemctl", "disable", name], check=False, capture_output=True)
        p = _systemd_path(name)
        if p.exists():
            p.unlink()
            print(f"  [-] Removed {p}")
    subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)
    print("✓ Systemd services removed.")


def restart_all(qq: str | None = None) -> None:
    """Restart both NapCat and Hermes Gateway."""
    import time

    # Prefer systemd if installed
    if _systemd_path(_NAPCAT_SERVICE_NAME).exists():
        subprocess.run(
            ["systemctl", "restart", _NAPCAT_SERVICE_NAME, _GATEWAY_SERVICE_NAME],
            check=True,
        )
        print("✓ Restarted via systemd.")
        return

    # Manual screen + process restart
    print("  Restarting NapCat...")
    stop_napcat()
    time.sleep(2)
    start_napcat(qq)

    print("  Restarting Hermes Gateway...")
    gateway_pid_file = Path.home() / ".hermes" / "gateway.pid"
    if gateway_pid_file.exists():
        try:
            import json
            data = json.loads(gateway_pid_file.read_text())
            pid = data.get("pid")
            if pid:
                subprocess.run(["kill", str(pid)], capture_output=True)
                time.sleep(2)
        except Exception:
            pass

    python = _find_hermes_python()
    hermes_dir = Path.home() / ".hermes" / "hermes-agent"
    log_file = Path(tempfile.gettempdir()) / "hermes-gateway.log"
    subprocess.Popen(
        [python, "-m", "hermes_cli.main", "gateway", "run", "--replace"],
        cwd=str(hermes_dir),
        stdout=open(log_file, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(f"✓ Gateway restarted (log → {log_file})")


def napcat_status() -> None:
    installed = is_napcat_installed()
    running = napcat_running() if installed else False

    print(f"\nNapCat status:")
    print(f"  installed: {'✓' if installed else '✗'}  ({qq_bin()})")
    if not installed:
        print(f"  → Run: hermes-napcat napcat start   (will offer to install)")
    print(f"  running:   {'✓' if running else '✗'}")
    if running:
        print(f"  attach:    screen -r {_SCREEN_SESSION}")

    cfg = onebot_config_path(None)
    print(f"  config:    {'✓' if cfg.exists() else '✗'}  ({cfg})")
    print()


# ── Setup wizard ───────────────────────────────────────────────────────────────

def setup_hermes_only(
    qq: str | None = None,
    ws_port: int = 18800,
    http_port: int = 18801,
    access_token: str = "",
    hermes_dir: str | None = None,
    admins: list[str] | None = None,
) -> None:
    """Patch Hermes + write onebot11 config. Does not install NapCat."""
    from .installer import install as _install_hermes

    print("\n=== hermes-napcat Setup ===\n")

    print("  [1/2] Patching Hermes Agent...")
    _install_hermes(hermes_dir)

    print("  [2/2] Writing NapCat onebot11 config...")
    cfg_path = write_napcat_config(qq, ws_port, http_port, access_token)
    print(f"  [+] Config written → {cfg_path}\n")

    _print_instructions(http_port, access_token, ws_port, qq=qq, include_napcat_steps=False, admins=admins)


def setup_with_napcat(
    qq: str | None = None,
    ws_port: int = 18800,
    http_port: int = 18801,
    access_token: str = "",
    hermes_dir: str | None = None,
    admins: list[str] | None = None,
) -> None:
    """Patch Hermes + install NapCat + write config. Does not start anything."""
    from .installer import install as _install_hermes

    print("\n=== hermes-napcat + NapCat Setup ===\n")

    print("  [1/3] Patching Hermes Agent...")
    _install_hermes(hermes_dir)

    if is_napcat_installed():
        print("  [2/3] NapCat already installed, skipping download.")
    else:
        print("  [2/3] Installing NapCat (NTQQ + NapCat layer)...")
        install_napcat()
        print("  [+] NapCat installed.\n")

    print("  [3/3] Writing NapCat onebot11 config...")
    cfg_path = write_napcat_config(qq, ws_port, http_port, access_token)
    print(f"  [+] Config written → {cfg_path}\n")

    _print_instructions(http_port, access_token, ws_port, qq=qq, include_napcat_steps=True, admins=admins)


def _hermes_config_path() -> Path:
    return Path.home() / ".hermes" / "config.yaml"


def _get_qq_from_config() -> str | None:
    """Read the saved QQ number from ~/.hermes/config.yaml."""
    try:
        import yaml
        p = _hermes_config_path()
        if not p.exists():
            return None
        with open(p, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        qq = str(cfg.get("platforms", {}).get("napcat", {}).get("extra", {}).get("self_id", ""))
        return qq or None
    except Exception:
        return None


def _napcat_platform_block(
    http_port: int,
    access_token: str,
    ws_port: int,
    qq: str | None,
    admins: list[str] | None = None,
) -> dict:
    return {
        "enabled": True,
        "extra": {
            "http_api": f"http://127.0.0.1:{http_port}",
            "access_token": access_token,
            "self_id": qq or "YOUR_QQ_NUMBER",
            "ws_port": ws_port,
            "dm_policy": "allowlist",
            "allow_from": [],
            "admins": admins or [],
        },
    }


def write_hermes_config(
    http_port: int,
    access_token: str,
    ws_port: int,
    qq: str | None,
    admins: list[str] | None = None,
) -> tuple[bool, str]:
    """Merge the napcat platform block into ~/.hermes/config.yaml.

    Returns (success, message).
    """
    try:
        import yaml
    except ImportError:
        try:
            _pip_install("pyyaml")
            import yaml
        except Exception as e:
            return False, f"pyyaml not installed and auto-install failed: {e}"

    cfg_path = _hermes_config_path()

    if cfg_path.exists():
        # Backup before modifying
        bak = cfg_path.with_suffix(".yaml.napcat.bak")
        if not bak.exists():
            import shutil
            shutil.copy2(cfg_path, bak)
        with cfg_path.open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        # Create minimal config so NapCat works out of the box
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg = {}

    # Merge platforms.napcat
    cfg.setdefault("platforms", {})
    if not isinstance(cfg["platforms"], dict):
        cfg["platforms"] = {}
    cfg["platforms"]["napcat"] = _napcat_platform_block(http_port, access_token, ws_port, qq, admins=admins)

    # Register toolsets: give NapCat the full Hermes CLI toolset + QQ tools
    cfg.setdefault("platform_toolsets", {})
    if not isinstance(cfg["platform_toolsets"], dict):
        cfg["platform_toolsets"] = {}
    cfg["platform_toolsets"]["napcat"] = ["hermes-cli", "hermes-napcat"]

    cfg.setdefault("group_sessions_per_user", False)

    with cfg_path.open("w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    return True, str(cfg_path)


def clean_hermes_config() -> tuple[bool, str]:
    """Remove napcat sections from ~/.hermes/config.yaml."""
    try:
        import yaml
    except ImportError:
        try:
            _pip_install("pyyaml")
            import yaml
        except Exception as e:
            return False, f"pyyaml not installed and auto-install failed: {e}"

    cfg_path = _hermes_config_path()
    if not cfg_path.exists():
        return False, f"Config not found: {cfg_path}"

    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    changed = False
    if isinstance(cfg.get("platforms"), dict) and "napcat" in cfg["platforms"]:
        del cfg["platforms"]["napcat"]
        changed = True
    if isinstance(cfg.get("platform_toolsets"), dict) and "napcat" in cfg["platform_toolsets"]:
        del cfg["platform_toolsets"]["napcat"]
        changed = True

    if changed:
        with cfg_path.open("w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return True, str(cfg_path)
    return True, "nothing to clean"


def _print_instructions(
    http_port: int,
    access_token: str,
    ws_port: int,
    qq: str | None,
    include_napcat_steps: bool,
    admins: list[str] | None = None,
) -> None:
    print("=" * 50)
    print("✓ Setup complete. Next steps:\n")

    step = 1
    if include_napcat_steps:
        print(f"{step}. 启动 NapCat（首次需扫码，之后自动登录）：")
        print(f"     hermes-napcat napcat start")
        print(f"     → 二维码直接显示在终端，扫码后自动完成登录\n")
        step += 1
    else:
        print(f"{step}. 确保 NapCat 已安装并运行：")
        print(f"     hermes-napcat napcat start")
        print(f"     （或先安装：hermes-napcat setup --with-napcat）\n")
        step += 1

    # Try to auto-write Hermes config
    ok, msg = write_hermes_config(http_port, access_token, ws_port, qq, admins=admins)
    if ok:
        print(f"{step}. Hermes config updated automatically → {msg}")
        if not qq:
            print(f"\n   ⚠  self_id is still YOUR_QQ_NUMBER — the bot won't recognise")
            print(f"      @mentions until you update it. Run:")
            print(f"      hermes-napcat setup --qq YOUR_ACTUAL_QQ_NUMBER")
        print()
    else:
        print(f"{step}. Add the following to ~/.hermes/config.yaml:\n")
        print("   platforms:")
        print("     napcat:")
        print("       enabled: true")
        print("       extra:")
        print(f'         http_api: "http://127.0.0.1:{http_port}"')
        print(f'         access_token: "{access_token}"')
        print(f'         self_id: "{qq or "YOUR_QQ_NUMBER"}"')
        print(f"         ws_port: {ws_port}")
        print('         dm_policy: "allowlist"')
        print("         allow_from: []")
        print("         admins: []             # QQ numbers that can use management commands")
        print(f"\n   (Auto-write failed: {msg})\n")
    step += 1

    print(f"{step}. Start Hermes as usual — NapCat will connect automatically.")
    print()
