"""安装助手测试：所有写入限定临时目录，网络和服务进程均替身。"""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import urllib.error

SCRIPT = Path(__file__).resolve().parents[1] / "skills/xhs-topic-scout/scripts/setup.py"
spec = importlib.util.spec_from_file_location("scout_setup", SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class Response(io.BytesIO):
    def __init__(self, data, url="https://release-assets.githubusercontent.com/package"):
        super().__init__(data)
        self.url = url

    def geturl(self):
        return self.url


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve() / "private"
        self.setup = helper.Setup(self.home)
        # 未显式mock的联网/启动也必须失败，防止测试意外安装或访问平台。
        self.patches = [mock.patch.object(helper.urllib.request, "urlopen", side_effect=AssertionError("unexpected download")),
                        mock.patch.object(helper, "api", side_effect=AssertionError("unexpected API")),
                        mock.patch.object(helper.subprocess, "Popen", side_effect=AssertionError("unexpected process")),
                        mock.patch.object(helper, "port_open", return_value=False),
                        mock.patch.object(helper, "executable_matches", return_value=True),
                        mock.patch.object(helper, "alive", return_value=False)]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def owned(self):
        self.setup.prepare()
        helper.private_write(self.setup.token_path, b"s" * 64)
        helper.private_write(self.setup.state_path, json.dumps({"pid": 123, "port": 18060, "release": helper.VERSION}).encode())
        return "s" * 64

    def answer(self, logged=False):
        def call(route, token=""):
            if route == "/health":
                return {"service": "xiaohongshu-mcp", "version": helper.VERSION}
            if not token:
                raise helper.SetupError("api", "401", "http_401")
            return {"is_logged_in": logged}
        return call

    def test_status_is_read_only_before_install(self):
        self.assertEqual(self.setup.status()["status"], "not_running")
        self.assertFalse(self.home.exists())

    def test_refuse_unowned_port_before_downloading(self):
        with mock.patch.object(helper, "port_open", return_value=True):
            with self.assertRaises(helper.SetupError) as caught:
                self.setup.ensure()
        self.assertEqual(caught.exception.code, "port_conflict")
        self.assertFalse(self.setup.token_path.exists())

    def test_existing_server_must_require_authentication(self):
        token = self.owned()
        with mock.patch.object(helper, "alive", return_value=True), mock.patch.object(helper, "api", return_value={"service": "xiaohongshu-mcp", "is_logged_in": True}):
            with self.assertRaises(helper.SetupError) as caught:
                self.setup.inspect(token, {"pid": 123, "port": 18060})
        self.assertEqual(caught.exception.code, "port_conflict")

    def test_reuse_authenticated_server_and_credentials(self):
        token = self.owned()
        original = self.setup.state_path.read_bytes()
        with mock.patch.object(helper, "port_open", return_value=True), mock.patch.object(helper, "alive", return_value=True), mock.patch.object(helper, "api", side_effect=self.answer(True)):
            for _ in range(2):
                self.assertEqual(self.setup.ensure()["status"], "ready")
        self.assertEqual(self.setup.token_path.read_text(), token)
        self.assertEqual(self.setup.state_path.read_bytes(), original)

    def test_wrong_token_is_not_adopted(self):
        token = self.owned()
        def reject(route, token=""):
            if route == "/health":
                return {"service": "xiaohongshu-mcp"}
            raise helper.SetupError("api", "401", "http_401")
        with mock.patch.object(helper, "alive", return_value=True), mock.patch.object(helper, "api", side_effect=reject):
            with self.assertRaises(helper.SetupError) as caught:
                self.setup.inspect(token, {"pid": 123, "port": 18060})
        self.assertEqual(caught.exception.code, "port_conflict")

    def test_download_verifies_digest_and_is_idempotent(self):
        self.setup.prepare()
        content = b"fictional executable for unit test"
        asset = {("Linux", "x86_64"): ("linux-amd64", hashlib.sha256(content).hexdigest())}
        with mock.patch.object(helper, "ASSETS", asset), mock.patch.object(helper.platform, "system", return_value="Linux"), mock.patch.object(helper.platform, "machine", return_value="x86_64"), mock.patch.object(helper.urllib.request, "urlopen", return_value=Response(content)) as download:
            self.setup.install()
            self.setup.install()
        self.assertEqual(download.call_count, 1)
        self.assertEqual(self.setup.binary.read_bytes(), content)
        self.assertEqual(stat.S_IMODE(self.setup.binary.stat().st_mode), 0o700)

    def test_bad_checksum_is_never_installed(self):
        self.setup.prepare()
        with mock.patch.object(helper.platform, "system", return_value="Linux"), mock.patch.object(helper.platform, "machine", return_value="x86_64"), mock.patch.object(helper.urllib.request, "urlopen", return_value=Response(b"corrupt")):
            with self.assertRaises(helper.SetupError) as caught:
                self.setup.install()
        self.assertEqual(caught.exception.code, "checksum_mismatch")
        self.assertFalse(self.setup.binary.exists())
        self.assertFalse(list(self.home.glob(".download-*")))

    def test_unsupported_architecture_is_explicit(self):
        self.setup.prepare()
        with mock.patch.object(helper.platform, "system", return_value="Linux"), mock.patch.object(helper.platform, "machine", return_value="aarch64"):
            with self.assertRaises(helper.SetupError) as caught:
                self.setup.install()
        self.assertEqual(caught.exception.code, "unsupported_platform")

    def test_missing_fcntl_returns_structured_unsupported_without_writes(self):
        with mock.patch.object(helper, "fcntl", None), contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = helper.main(["--home", str(self.home), "ensure"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stderr.getvalue())["code"], "unsupported_platform")
        self.assertFalse(self.home.exists())

    def test_start_binds_loopback_uses_private_environment_and_records_pid(self):
        process = mock.Mock(pid=456)
        process.poll.return_value = None
        with mock.patch.object(self.setup, "install"), mock.patch.object(helper, "alive", side_effect=lambda pid: pid == 456), mock.patch.object(helper, "port_open", side_effect=[False, True]), mock.patch.object(helper, "api", side_effect=self.answer(False)), mock.patch.object(helper.subprocess, "Popen", return_value=process) as start:
            result = self.setup.ensure()
        self.assertEqual(result["status"], "needs_login")
        argv = start.call_args.args[0]
        options = start.call_args.kwargs
        self.assertEqual(argv[1:], ["-port", "127.0.0.1:18060"])
        token = self.setup.token_path.read_text().strip()
        self.assertNotIn(token, json.dumps(result))
        self.assertNotIn(token, " ".join(argv))
        self.assertEqual(options["env"]["AUTH_TOKEN"], token)
        self.assertEqual(options["env"]["COOKIES_PATH"], str(self.home / "data/cookies.json"))
        self.assertEqual(options["umask"], 0o077)
        self.assertEqual(stat.S_IMODE(self.home.stat().st_mode), 0o700)
        for path in (self.setup.token_path, self.setup.state_path, self.setup.log_path):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(json.loads(self.setup.state_path.read_text())["pid"], 456)

    def test_start_failure_is_not_reported_as_ready(self):
        process = mock.Mock(pid=456)
        process.poll.return_value = 1
        with mock.patch.object(self.setup, "install"), mock.patch.object(helper.subprocess, "Popen", return_value=process):
            with self.assertRaises(helper.SetupError) as caught:
                self.setup.ensure()
        self.assertEqual(caught.exception.code, "process_exited")

    def test_reused_pid_is_ignored_without_killing_the_other_process(self):
        token = self.owned()
        process = mock.Mock(pid=456)
        process.poll.return_value = None
        with mock.patch.object(helper, "alive", return_value=True), mock.patch.object(helper, "executable_matches", side_effect=lambda pid, binary: pid == 456):
            self.assertEqual(self.setup.status()["status"], "not_running")
            with mock.patch.object(self.setup, "install") as install, mock.patch.object(helper, "port_open", side_effect=[False, True]), mock.patch.object(helper, "api", side_effect=self.answer(False)), mock.patch.object(helper.subprocess, "Popen", return_value=process) as start, mock.patch.object(helper.os, "kill") as kill:
                self.assertEqual(self.setup.ensure()["status"], "needs_login")
        install.assert_called_once()
        start.assert_called_once()
        kill.assert_not_called()
        process.terminate.assert_not_called()
        self.assertEqual(json.loads(self.setup.state_path.read_text())["pid"], 456)
        self.assertEqual(self.setup.token_path.read_text(), token)

    def test_matching_process_still_starting_is_reused_without_spawn(self):
        self.owned()
        with mock.patch.object(helper, "alive", return_value=True):
            self.assertEqual(self.setup.status()["status"], "starting")
            with mock.patch.object(helper, "port_open", side_effect=[False, False, True]), mock.patch.object(helper, "api", side_effect=self.answer(True)), mock.patch.object(helper.time, "sleep"), mock.patch.object(self.setup, "install") as install:
                self.assertEqual(self.setup.ensure()["status"], "ready")
        install.assert_not_called()
        self.assertEqual(json.loads(self.setup.state_path.read_text())["pid"], 123)

    def test_login_writes_only_private_qr_and_returns_no_base64(self):
        token = self.owned()
        png = b"\x89PNG\r\n\x1a\n" + b"fictional qr test data"
        encoded = base64.b64encode(png).decode()
        with mock.patch.object(self.setup, "ensure", return_value={"logged_in": False}), mock.patch.object(helper, "api", return_value={"is_logged_in": False, "img": "data:image/png;base64," + encoded}):
            result = self.setup.login()
        self.assertEqual(Path(result["qr_path"]).read_bytes(), png)
        self.assertEqual(stat.S_IMODE(Path(result["qr_path"]).stat().st_mode), 0o600)
        self.assertNotIn(token, json.dumps(result))
        self.assertNotIn(encoded, json.dumps(result))
        self.assertEqual(result["expires_in_seconds"], 240)

    def test_login_invalid_qr_fails_without_file(self):
        self.owned()
        with mock.patch.object(self.setup, "ensure", return_value={"logged_in": False}), mock.patch.object(helper, "api", return_value={"is_logged_in": False, "img": "https://untrusted.invalid/image"}):
            with self.assertRaises(helper.SetupError):
                self.setup.login()
        self.assertFalse((self.home / "login-qr.png").exists())

    def test_run_passes_credentials_only_in_child_environment(self):
        token = self.owned()
        with mock.patch.object(self.setup, "ensure", return_value={"logged_in": True}), mock.patch.object(helper.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            self.assertEqual(self.setup.run(["search", "--keywords", "AI"]), 0)
        argv, env = run.call_args.args[0], run.call_args.kwargs["env"]
        self.assertNotIn(token, " ".join(argv))
        self.assertEqual(env["XHS_MCP_TOKEN"], token)
        self.assertEqual(env["XHS_MCP_URL"], helper.BASE)
        self.assertIn(str(self.home / "reports"), argv)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_run_does_not_forward_environment_proxies(self):
        self.owned()
        proxy_env = {"HTTP_PROXY": "http://proxy.invalid:8080", "https_proxy": "http://other.invalid:8080",
                     "ALL_PROXY": "socks5://proxy.invalid:1080", "no_proxy": "example.org", "OTHER_SETTING": "keep"}
        with mock.patch.dict(helper.os.environ, proxy_env), mock.patch.object(self.setup, "ensure", return_value={"logged_in": True}), mock.patch.object(helper.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            self.setup.run(["check"])
            self.assertEqual(helper.os.environ["HTTP_PROXY"], proxy_env["HTTP_PROXY"])
        env = run.call_args.kwargs["env"]
        self.assertEqual({key.lower() for key in env if key.lower().endswith("_proxy")}, {"no_proxy"})
        self.assertEqual(env["NO_PROXY"], "127.0.0.1,localhost,::1")
        self.assertEqual(env["no_proxy"], env["NO_PROXY"])
        self.assertEqual(env["OTHER_SETTING"], "keep")

    def test_run_cannot_override_service_or_use_demo(self):
        for args in (["sample"], ["search", "--url=https://elsewhere.invalid"], []):
            with self.assertRaises(helper.SetupError):
                self.setup.run(args)

    def test_main_needs_login_and_error_contracts_do_not_leak(self):
        with mock.patch.object(helper.Setup, "ensure", return_value={"status": "needs_login", "logged_in": False}), contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = helper.main(["--home", str(self.home), "ensure"])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "needs_login")
        with mock.patch.object(helper.Setup, "ensure", side_effect=helper.SetupError("download", "下载失败", "download_failed")), contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = helper.main(["--home", str(self.home), "ensure"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stderr.getvalue())["stage"], "download")


class ApiTests(unittest.TestCase):
    def test_api_uses_no_proxy_and_rejects_redirects(self):
        fake = mock.Mock()
        fake.open.return_value = Response(b'{"success":true,"data":{"is_logged_in":false}}')
        with mock.patch.object(helper.urllib.request, "build_opener", return_value=fake) as build:
            self.assertEqual(helper.api("/api/v1/login/status", "DUMMY")["is_logged_in"], False)
        handlers = build.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], helper.NoRedirect)
        self.assertIsNone(handlers[1].redirect_request(None, None, 302, "", {}, "https://elsewhere.invalid"))
        self.assertEqual(fake.open.call_args.args[0].get_header("Authorization"), "Bearer DUMMY")

    def test_api_network_and_invalid_json_are_explicit_errors(self):
        for reply, expected in ((urllib.error.URLError("offline"), "connection_failed"), (Response(b"no json"), "invalid_response")):
            fake = mock.Mock()
            if isinstance(reply, Exception):
                fake.open.side_effect = reply
            else:
                fake.open.return_value = reply
            with mock.patch.object(helper.urllib.request, "build_opener", return_value=fake):
                with self.assertRaises(helper.SetupError) as caught:
                    helper.api("/health")
            self.assertEqual(caught.exception.code, expected)


class ProcessIdentityTests(unittest.TestCase):
    def test_linux_requires_exact_executable_path(self):
        binary = Path("/private/example/xiaohongshu-mcp")
        real_readlink = helper.os.readlink
        with mock.patch.object(helper.platform, "system", return_value="Linux"), mock.patch.object(helper.os, "readlink", side_effect=lambda path: "/usr/bin/unrelated" if str(path).startswith("/proc/") else real_readlink(path)):
            self.assertFalse(helper.executable_matches(123, binary))
        with mock.patch.object(helper.platform, "system", return_value="Linux"), mock.patch.object(helper.os, "readlink", side_effect=lambda path: str(binary) if str(path).startswith("/proc/") else real_readlink(path)):
            self.assertTrue(helper.executable_matches(123, binary))

    def test_macos_checks_ps_executable_and_timeout_is_not_ownership(self):
        binary = Path("/private/example/xiaohongshu-mcp")
        with mock.patch.object(helper.platform, "system", return_value="Darwin"), mock.patch.object(helper.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=str(binary) + "\n")) as ps:
            self.assertTrue(helper.executable_matches(123, binary))
        self.assertEqual(ps.call_args.args[0], ["/bin/ps", "-p", "123", "-o", "comm="])
        with mock.patch.object(helper.platform, "system", return_value="Darwin"), mock.patch.object(helper.subprocess, "run", side_effect=helper.subprocess.TimeoutExpired("ps", 3)):
            self.assertFalse(helper.executable_matches(123, binary))


if __name__ == "__main__":
    unittest.main()
