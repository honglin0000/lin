#!/usr/bin/env python3
"""在当前电脑准备小红书数据服务；Python 3.9+，仅使用标准库。"""
import argparse
import base64
import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import fcntl
except ImportError:
    fcntl = None

VERSION = "v2.5.5"
PORT = 18060
BASE = "http://127.0.0.1:%s" % PORT
ASSETS = {
    ("Linux", "x86_64"): ("linux-amd64", "a4e99322156e7a169466e793045dadc3306c0792db3eade603e030cc0c1c2e3a"),
    ("Darwin", "arm64"): ("darwin-arm64", "fad3633fda4a8060e66e2941bc8fc5460326c7cb4e58a32485a9e2c9408e95a8"),
}
START_TIMEOUT = 300


class SetupError(Exception):
    def __init__(self, stage, message, code="setup_failed"):
        super().__init__(message)
        self.stage, self.code = stage, code


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def private_write(path, data, mode=0o600):
    """同目录原子写入，临时文件和最终文件均不向其他用户开放。"""
    fd, name = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def alive(pid):
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def executable_matches(pid, binary):
    """PID 可能被复用；核对实际可执行文件，不能仅凭存活就认作自己的。"""
    try:
        if platform.system() == "Linux":
            executable = os.readlink("/proc/%s/exe" % pid)
        elif platform.system() == "Darwin":
            result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "comm="],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    text=True, timeout=3, check=False)
            if result.returncode != 0:
                return False
            executable = result.stdout.strip()
        else:
            return False
        return executable.startswith("/") and Path(executable).resolve() == binary.resolve()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        return False


def port_open():
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
            return True
    except OSError:
        return False


def api(route, token=""):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + route, headers=headers)
    # 回环调用不经过环境代理，也不跟随重定向转发凭据。
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=65) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise SetupError("api", "数据服务响应过大。", "invalid_response")
        payload = json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise SetupError("api", "数据服务返回 HTTP %s。" % exc.code, "http_%s" % exc.code) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise SetupError("api", "无法连接数据服务或请求超时。", "connection_failed") from None
    except (ValueError, UnicodeError):
        raise SetupError("api", "数据服务没有返回有效 JSON。", "invalid_response") from None
    if not isinstance(payload, dict) or payload.get("success") is not True or not isinstance(payload.get("data"), dict):
        raise SetupError("api", "数据服务返回失败或格式不符。", "invalid_response")
    return payload["data"]


class Setup:
    def __init__(self, home=None):
        self.home = Path(home or os.environ.get("XHS_SCOUT_HOME") or "~/.local/share/xhs-topic-scout").expanduser().resolve()
        self.token_path = self.home / "auth-token"
        self.state_path = self.home / "service.json"
        self.log_path = self.home / "service.log"
        self.binary = self.home / ("xiaohongshu-mcp-" + VERSION)

    def prepare(self):
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.home.chmod(0o700)
        for name in ("data", "cache", "reports"):
            folder = self.home / name
            if folder.is_symlink():
                raise SetupError("files", "私有目录不能使用符号链接。", "unsafe_path")
            folder.mkdir(mode=0o700, exist_ok=True)
            folder.chmod(0o700)

    @contextlib.contextmanager
    def lock(self):
        if fcntl is None:
            raise SetupError("platform", "当前平台不支持此部署助手；仅支持 Linux x86_64 和 Apple Silicon macOS。", "unsupported_platform")
        self.prepare()
        path = self.home / "setup.lock"
        if path.is_symlink():
            raise SetupError("files", "锁文件不能使用符号链接。", "unsafe_path")
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def credentials(self):
        if self.token_path.is_symlink() or self.state_path.is_symlink():
            raise SetupError("files", "服务凭据不能使用符号链接。", "unsafe_path")
        try:
            token = self.token_path.read_text(encoding="utf-8").strip() if self.token_path.exists() else ""
            state = json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists() else {}
        except (OSError, ValueError, UnicodeError):
            raise SetupError("files", "无法读取私有服务状态；请检查文件，不要删除其他服务的配置。", "invalid_state") from None
        if not isinstance(state, dict) or (token and (len(token) < 32 or any(c.isspace() for c in token))):
            raise SetupError("files", "私有服务状态或凭据格式不符。", "invalid_state")
        return token, state

    def owns(self, pid):
        return alive(pid) and executable_matches(pid, self.binary)

    def inspect(self, token, state):
        if not token or not self.owns(state.get("pid")) or state.get("port") != PORT:
            raise SetupError("ownership", "18060 端口已有无法确认归属的服务；未接管或停止它。", "port_conflict")
        health = api("/health")
        if health.get("service") != "xiaohongshu-mcp":
            raise SetupError("ownership", "18060 端口不是本助手的数据服务。", "port_conflict")
        # 验证它确实要求鉴权，不能把接受任意 token 的无鉴权服务当作自己的。
        try:
            api("/api/v1/login/status")
        except SetupError as exc:
            if exc.code != "http_401":
                raise SetupError("ownership", "无法验证服务鉴权；未接管现有服务。", "port_conflict") from None
        else:
            raise SetupError("ownership", "现有服务未要求鉴权；未接管它。", "port_conflict")
        try:
            data = api("/api/v1/login/status", token)
        except SetupError as exc:
            if exc.code == "http_401":
                raise SetupError("ownership", "现有服务与私有凭据不匹配；未接管它。", "port_conflict") from None
            raise
        if not isinstance(data.get("is_logged_in"), bool):
            raise SetupError("login_status", "服务没有返回明确的登录状态。", "invalid_response")
        logged = data["is_logged_in"]
        return {"status": "ready" if logged else "needs_login", "stage": "login_status", "connected": True,
                "logged_in": logged, "message": "数据服务和小红书登录已就绪。" if logged else "数据服务已就绪，请运行 login 获取二维码。"}

    def status(self):
        token, state = self.credentials()
        if not port_open():
            running = self.owns(state.get("pid"))
            return {"status": "starting" if running else "not_running", "stage": "status", "connected": False,
                    "logged_in": False, "message": "服务进程仍在启动，请运行 ensure 等待自检。" if running else "本助手的数据服务未运行，请运行 ensure。"}
        return self.inspect(token, state)

    def install(self):
        asset = ASSETS.get((platform.system(), platform.machine()))
        if not asset:
            raise SetupError("platform", "仅支持 Linux x86_64 和 Apple Silicon macOS；当前平台没有已核实的安装包。", "unsupported_platform")
        suffix, expected = asset
        if self.binary.is_symlink():
            raise SetupError("files", "程序文件不能使用符号链接。", "unsafe_path")
        if self.binary.exists() and hashlib.sha256(self.binary.read_bytes()).hexdigest() == expected:
            self.binary.chmod(0o700)
            return
        url = "https://github.com/xpzouying/xiaohongshu-mcp/releases/download/%s/xiaohongshu-mcp-%s" % (VERSION, suffix)
        fd, temporary = tempfile.mkstemp(prefix=".download-", dir=str(self.home))
        try:
            digest, total = hashlib.sha256(), 0
            with os.fdopen(fd, "wb") as stream:
                os.fchmod(stream.fileno(), 0o700)
                with urllib.request.urlopen(url, timeout=90) as response:
                    final = urllib.parse.urlsplit(response.geturl())
                    if final.scheme != "https" or not (final.hostname == "github.com" or (final.hostname or "").endswith(".githubusercontent.com")):
                        raise SetupError("download", "下载被重定向到未认可的来源。", "invalid_download")
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > 100 * 1024 * 1024:
                            raise SetupError("download", "安装包超过预期大小。", "invalid_download")
                        digest.update(chunk)
                        stream.write(chunk)
            if digest.hexdigest() != expected:
                raise SetupError("download", "官方安装包 SHA256 校验失败，未运行下载的文件。", "checksum_mismatch")
            os.replace(temporary, self.binary)
        except (urllib.error.URLError, TimeoutError, OSError):
            raise SetupError("download", "下载官方安装包失败，请检查网络和目录权限后重试。", "download_failed") from None
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def ensure(self):
        with self.lock():
            token, state = self.credentials()
            for path in (self.token_path, self.state_path):
                if path.exists():
                    path.chmod(0o600)
            if port_open():
                return self.inspect(token, state)
            process = None
            if not self.owns(state.get("pid")):
                self.install()
                if not token:
                    token = secrets.token_urlsafe(48)
                    private_write(self.token_path, (token + "\n").encode("utf-8"))
                self.token_path.chmod(0o600)
                if self.log_path.is_symlink():
                    raise SetupError("files", "日志文件不能使用符号链接。", "unsafe_path")
                env = os.environ.copy()
                env.update({"AUTH_TOKEN": token, "COOKIES_PATH": str(self.home / "data" / "cookies.json"),
                            "XDG_CACHE_HOME": str(self.home / "cache")})
                with open(self.log_path, "ab") as log:
                    os.fchmod(log.fileno(), 0o600)
                    process = subprocess.Popen([str(self.binary), "-port", "127.0.0.1:%s" % PORT],
                                               cwd=str(self.home), env=env, stdin=subprocess.DEVNULL,
                                               stdout=log, stderr=log, start_new_session=True, umask=0o077)
                state = {"pid": process.pid, "port": PORT, "release": VERSION}
                try:
                    private_write(self.state_path, json.dumps(state).encode("utf-8"))
                except OSError:
                    process.terminate()  # 只撤销刚由本次创建且尚未登记的进程。
                    raise
            elif not token:
                raise SetupError("ownership", "记录中的服务进程缺少私有凭据，未启动第二个服务。", "invalid_state")
            deadline = time.monotonic() + START_TIMEOUT
            while time.monotonic() < deadline:
                running = process.poll() is None if process is not None else self.owns(state.get("pid"))
                if not running:
                    raise SetupError("startup", "服务启动失败。请检查日志；若提示缺少共享库，用浏览器文件的 ldd 检查缺项。本助手不安装系统包。", "process_exited")
                if port_open():
                    return self.inspect(token, state)
                time.sleep(1)
            raise SetupError("startup", "等待服务启动超时。首次运行需下载内置浏览器，请检查日志和网络后再次运行 ensure。", "startup_timeout")

    def login(self):
        result = self.ensure()
        if result["logged_in"]:
            return result
        token, _ = self.credentials()
        data = api("/api/v1/login/qrcode", token)
        if data.get("is_logged_in") is True:
            return self.status()
        src = data.get("img", "")
        prefix = "data:image/png;base64,"
        if not isinstance(src, str) or not src.startswith(prefix):
            raise SetupError("login", "服务未返回可用的 PNG 二维码，请检查服务日志。", "invalid_qrcode")
        try:
            content = base64.b64decode(src[len(prefix):], validate=True)
        except (ValueError, TypeError):
            raise SetupError("login", "二维码图片编码无效。", "invalid_qrcode") from None
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise SetupError("login", "二维码图片格式无效。", "invalid_qrcode")
        path = self.home / "login-qr.png"
        private_write(path, content)
        return {"status": "needs_login", "stage": "login", "connected": True, "logged_in": False,
                "qr_path": str(path), "expires_in_seconds": 240,
                "message": "请展示此本地二维码，用小红书扫码；扫码后运行 status。再次获取二维码会使前一张失效。"}

    def run(self, arguments):
        if not arguments or arguments[0] not in ("search", "check") or any(arg == "--url" or arg.startswith("--url=") for arg in arguments):
            raise SetupError("arguments", "run 后请填写 search 及搜索参数，或 check；服务地址由本助手自动配置。", "invalid_arguments")
        result = self.ensure()
        if not result["logged_in"]:
            return result
        token, _ = self.credentials()
        # scout 仅访问此回环服务；不让继承的环境代理接触鉴权请求。
        # 同时设置 no_proxy，避免系统代理在环境代理清空后成为后备来源。
        env = {key: value for key, value in os.environ.items() if not key.lower().endswith("_proxy")}
        env.update({"XHS_MCP_URL": BASE, "XHS_MCP_TOKEN": token,
                    "NO_PROXY": "127.0.0.1,localhost,::1", "no_proxy": "127.0.0.1,localhost,::1"})
        args = list(arguments)
        if args[0] == "search" and not any(arg == "--output-dir" or arg.startswith("--output-dir=") for arg in args):
            args += ["--output-dir", str(self.home / "reports")]
        scout = Path(__file__).resolve().with_name("scout.py")
        return subprocess.run([sys.executable, str(scout)] + args, env=env, check=False).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description="自动准备当前电脑的小红书热点数据服务，不开放公网端口。")
    parser.add_argument("--home", help="私有数据目录；默认使用 XHS_SCOUT_HOME 或用户数据目录")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("ensure", "login", "status"):
        sub.add_parser(name)
    run = sub.add_parser("run")
    run.add_argument("scout_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    setup = Setup(args.home)
    try:
        result = setup.run(args.scout_args) if args.command == "run" else getattr(setup, args.command)()
        if isinstance(result, int):
            return result
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("status") == "ready" else 3
    except SetupError as exc:
        print(json.dumps({"status": "error", "stage": exc.stage, "code": exc.code,
                          "message": str(exc), "log_path": str(setup.log_path)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except OSError:
        print(json.dumps({"status": "error", "stage": "files_or_process", "code": "local_failure",
                          "message": "本地目录或进程操作失败，请检查权限和日志。", "log_path": str(setup.log_path)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
