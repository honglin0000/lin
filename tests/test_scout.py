"""Offline regression tests. Every note, author and access value below is fictional.

The integration tests use a real HTTP server bound only to 127.0.0.1. They never
contact Xiaohongshu, GitHub, or any other external service.
"""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock


# Keep all test artifacts inside tests/, including when importing the script.
sys.dont_write_bytecode = True
TESTS = Path(__file__).resolve().parent
SCRIPT = TESTS.parent / "skills" / "xhs-topic-scout" / "scripts" / "scout.py"
SPEC = importlib.util.spec_from_file_location("scout_under_test", SCRIPT)
scout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scout)
FIXED_NOW = dt.datetime(2026, 10, 14, 12, 0, tzinfo=scout.TZ)


def fictional_feed(name):
    return {
        "id": "fixture-fictional-" + name,
        "modelType": "note",
        "xsecToken": "FICTIONAL_TEST_VALUE_NOT_A_REAL_TOKEN",
        "noteCard": {"displayTitle": "虚构测试笔记：" + name},
    }


def fictional_detail(name, published, metrics=None):
    return {"data": {
        "note": {
            "noteId": "fixture-fictional-" + name,
            "title": "虚构测试笔记：" + name,
            "time": published,
            "desc": "虚构测试正文，仅用于离线测试，不是实际小红书内容。",
            "user": {"nickname": "虚构测试作者", "userId": "fixture-fictional-author"},
            "interactInfo": metrics or {},
        },
        "comments": {"list": [{"content": "虚构测试评论，仅用于检验数据读取。"}]},
    }}


@contextlib.contextmanager
def local_source(responder):
    """Serve the real API boundary locally and retain observed HTTP requests."""
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length)) if length else None
            request = {"method": self.command, "path": self.path, "body": body}
            requests.append(request)
            reply = responder(self.command, self.path, body)
            status, payload = reply[:2]
            extra_headers = reply[2] if len(reply) > 2 else {}
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            for key, value in extra_headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.02}, daemon=True)
    worker.start()
    try:
        yield "http://127.0.0.1:%s" % server.server_port, requests
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def scenario(feeds=None, details=None, logged_in=True, fail_search=False,
             detail_failures=(), search_failures=()):
    feeds = feeds or []
    details = details or {}

    def respond(method, path, body):
        if (method, path) == ("GET", "/api/v1/login/status"):
            return 200, {"success": True, "data": {"is_logged_in": logged_in}}
        if (method, path) == ("POST", "/api/v1/feeds/search"):
            if fail_search or body["keyword"] in search_failures:
                return 503, {"success": False, "message": "虚构测试服务故障"}
            returned = feeds.get(body["keyword"], []) if isinstance(feeds, dict) else feeds
            return 200, {"success": True, "data": {"feeds": returned}}
        if (method, path) == ("POST", "/api/v1/feeds/detail"):
            if body["feed_id"] in detail_failures:
                return 500, {"success": False, "message": "虚构测试详情故障"}
            return 200, {"success": True, "data": details[body["feed_id"]]}
        return 404, {"success": False, "message": "未预期的测试路由"}

    return respond


class ScoutIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {
            "XHS_MCP_TOKEN": "", "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost", "PYTHONDONTWRITEBYTECODE": "1",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def cli(self, url, output, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "search", "--url", url,
             "--keywords", "虚构测试关键词甲", "--output-dir", str(output), *extra],
            capture_output=True, text=True, timeout=15, env=os.environ.copy(),
        )

    def test_cli_real_http_exports_and_posts_filters_and_deduplicates(self):
        recent = int((dt.datetime.now(scout.TZ) - dt.timedelta(days=1)).timestamp() * 1000)
        a, b = fictional_feed("甲"), fictional_feed("乙")
        responder = scenario(
            feeds={"虚构测试关键词甲": [a, a, b], "虚构测试关键词乙": [b, a]},
            details={a["id"]: fictional_detail("甲", recent, {"likedCount": "1.2万", "collectedCount": "300", "commentCount": "21"}),
                     b["id"]: fictional_detail("乙", recent, {"likedCount": "999999999"})},
        )
        with local_source(responder) as (url, requests), tempfile.TemporaryDirectory(dir=TESTS) as output:
            result = self.cli(url + "/mcp", output, "--keywords", "虚构测试关键词甲", "虚构测试关键词乙", "虚构测试关键词甲")
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = json.loads(result.stdout)
            report = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
            markdown = Path(paths["markdown"]).read_text(encoding="utf-8")
            self.assertFalse(report["demo"])
            self.assertTrue(report["partial"], "缺失互动指标必须标明部分结果")
            self.assertEqual(report["summary"]["unique_search_notes"], 2)
            self.assertEqual(len(report["notes"]), 2)
            self.assertEqual(report["notes"][0]["metrics"]["likes"], 12000)
            self.assertEqual(set(report["notes"][0]["keywords"]), {"虚构测试关键词甲", "虚构测试关键词乙"})
            self.assertEqual(report["notes"][1]["metrics"]["saves"], None)
            self.assertIsNone(report["notes"][1]["sample_score"])
            self.assertEqual(report["notes"][0]["comments_read"], 1)
            self.assertIn("不是小红书全站热榜", markdown)
            self.assertIn("单次采样不能证明增长趋势", markdown)
            self.assertIn("未取得", markdown)
            searches = [r for r in requests if r["path"].endswith("/feeds/search")]
            self.assertEqual(len(searches), 4)
            self.assertTrue(all(r["method"] == "POST" for r in searches))
            self.assertEqual({r["body"]["filters"]["sort_by"] for r in searches}, {"最新", "最多收藏"})
            self.assertTrue(all(r["body"]["filters"]["publish_time"] == "一周内" for r in searches))
            detail_requests = [r for r in requests if r["path"].endswith("/feeds/detail")]
            self.assertEqual(len(detail_requests), 2)
            self.assertTrue(all(r["body"]["load_all_comments"] is False for r in detail_requests))
            self.assertEqual({r["body"]["feed_id"] for r in detail_requests}, {a["id"], b["id"]})

    def test_millisecond_dates_and_unknown_old_future_exclusion(self):
        times = {
            "毫秒日期": int((FIXED_NOW - dt.timedelta(days=2)).timestamp() * 1000),
            "未知日期": None,
            "过期日期": int((FIXED_NOW - dt.timedelta(days=8)).timestamp() * 1000),
            "未来日期": int((FIXED_NOW + dt.timedelta(days=1)).timestamp() * 1000),
        }
        feeds = [fictional_feed(name) for name in times]
        details = {"fixture-fictional-" + name: fictional_detail(name, when) for name, when in times.items()}
        with local_source(scenario(feeds, details)) as (url, _):
            report = scout.collect(scout.Client(url, token=""), ["虚构日期测试"], 7, 10, 30, now=FIXED_NOW)
        self.assertEqual([n["id"] for n in report["notes"]], ["fixture-fictional-毫秒日期"])
        self.assertEqual(report["notes"][0]["published_at"], "2026-10-12T12:00:00+08:00")
        self.assertEqual({n["date_status"] for n in report["excluded_notes"]}, {"unknown", "outside_window", "future"})
        self.assertEqual(report["summary"]["excluded_by_date"], 3)
        self.assertTrue(report["partial"])
        self.assertEqual(report["notes"][0]["metrics"], {"likes": None, "saves": None, "comments": None})
        self.assertIsNone(report["notes"][0]["sample_score"])
        rendered = scout.render(report)
        for marker in ("发布时间未确认", "超出时间范围", "发布时间晚于采集时间", "不参加排名"):
            self.assertIn(marker, rendered)
        ranking, remaining = rendered.split("### 指标不全的待核实线索（不参加排名）", 1)
        unranked, _ = remaining.split("排序说明：", 1)
        self.assertNotIn("虚构测试笔记：毫秒日期", ranking)
        self.assertIn("虚构测试笔记：毫秒日期", unranked)
        self.assertIn("点赞 未取得，收藏 未取得，评论 未取得", unranked)

    def test_date_uncertainty_alone_marks_report_partial(self):
        complete_metrics = {"likedCount": 0, "collectedCount": 0, "commentCount": 0}
        for published, expected_partial in ((None, True), ((FIXED_NOW + dt.timedelta(days=1)).isoformat(), True),
                                            ((FIXED_NOW - dt.timedelta(days=8)).isoformat(), False),
                                            (FIXED_NOW.isoformat(), False)):
            with self.subTest(published=published):
                feed = fictional_feed("独立日期检查")
                details = {feed["id"]: fictional_detail("独立日期检查", published, complete_metrics)}
                with local_source(scenario([feed], details)) as (url, _):
                    report = scout.collect(scout.Client(url, token=""), ["虚构关键词"], 7, 10, 30, now=FIXED_NOW)
                self.assertEqual(report["partial"], expected_partial)

    def test_partial_detail_failure_preserves_valid_evidence(self):
        a, b = fictional_feed("有效详情"), fictional_feed("失败详情")
        details = {a["id"]: fictional_detail("有效详情", FIXED_NOW.isoformat(), {"likedCount": "0"})}
        with local_source(scenario([a, b], details, detail_failures=[b["id"]])) as (url, _):
            report = scout.collect(scout.Client(url, token=""), ["虚构关键词"], 7, 10, 30, now=FIXED_NOW)
        self.assertTrue(report["partial"])
        self.assertEqual(len(report["notes"]), 1)
        self.assertEqual(report["notes"][0]["metrics"]["likes"], 0)
        self.assertIsNone(report["notes"][0]["metrics"]["saves"])
        self.assertEqual(report["errors"][0]["stage"], "detail")
        self.assertEqual(report["errors"][0]["note_id"], b["id"])
        self.assertEqual(report["summary"]["detail_attempts"], 2)
        self.assertIn("部分采样结果", scout.render(report))

    def test_mismatched_detail_id_is_rejected_as_evidence(self):
        a, b = fictional_feed("正确笔记"), fictional_feed("被错误匹配的笔记")
        details = {
            a["id"]: fictional_detail("正确笔记", FIXED_NOW.isoformat(), {"likedCount": 1, "collectedCount": 1, "commentCount": 1}),
            b["id"]: fictional_detail("另一篇笔记", FIXED_NOW.isoformat(), {"likedCount": 999, "collectedCount": 999, "commentCount": 999}),
        }
        with local_source(scenario([a, b], details)) as (url, _):
            report = scout.collect(scout.Client(url, token=""), ["虚构关键词"], 7, 10, 30, now=FIXED_NOW)
        self.assertEqual([note["id"] for note in report["notes"]], [a["id"]])
        self.assertTrue(report["partial"])
        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(report["errors"][0]["stage"], "detail")
        self.assertEqual(report["errors"][0]["note_id"], b["id"])

    def test_http_redirects_are_rejected_without_contacting_the_destination(self):
        for status in (302, 307):
            with self.subTest(status=status), local_source(scenario()) as (destination, received):
                def redirect(method, path, body):
                    return status, {"fictional": "离线重定向测试"}, {"Location": destination + "/api/v1/login/status"}

                with local_source(redirect) as (source, original):
                    with self.assertRaises(scout.SourceError):
                        scout.Client(source, token="FICTIONAL_UNITTEST_VALUE").call("GET", "/login/status")
                self.assertEqual(len(original), 1)
                self.assertEqual(received, [], "不得向重定向目标发送请求或鉴权头")

    def test_redirect_cannot_reach_a_disallowed_route_on_same_server(self):
        source_address = {}

        def redirect(method, path, body):
            if path == "/api/v1/login/status":
                return 302, {}, {"Location": source_address["url"] + "/api/v1/feeds/publish"}
            return 200, {"success": True, "data": {"is_logged_in": True}}

        with local_source(redirect) as (url, requests):
            source_address["url"] = url
            with self.assertRaises(scout.SourceError):
                scout.Client(url, token="").call("GET", "/login/status")
        self.assertEqual([request["path"] for request in requests], ["/api/v1/login/status"])

    def test_partial_keyword_search_failure_is_reported(self):
        a = fictional_feed("部分搜索")
        responder = scenario([a], {a["id"]: fictional_detail("部分搜索", FIXED_NOW.isoformat())}, search_failures=["虚构失败关键词"])
        with local_source(responder) as (url, _):
            report = scout.collect(scout.Client(url, token=""), ["虚构成功关键词", "虚构失败关键词"], 7, 10, 30, now=FIXED_NOW)
        self.assertTrue(report["partial"])
        self.assertEqual(report["summary"]["searches_succeeded"], 2)
        self.assertEqual(report["summary"]["searches_requested"], 4)
        self.assertEqual(len(report["notes"]), 1)
        self.assertEqual(len(report["errors"]), 2)
        self.assertTrue(all(error["stage"] == "search" for error in report["errors"]))

    def test_not_logged_in_does_not_search_or_export(self):
        with local_source(scenario(logged_in=False)) as (url, requests), tempfile.TemporaryDirectory(dir=TESTS) as output:
            result = self.cli(url, output)
            self.assertEqual(result.returncode, 2)
            self.assertIn("尚未登录", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(list(Path(output).iterdir()), [])
            self.assertEqual([(r["method"], r["path"]) for r in requests], [("GET", "/api/v1/login/status")])

    def test_all_searches_fail_without_exporting_a_hot_report(self):
        with local_source(scenario(fail_search=True)) as (url, requests), tempfile.TemporaryDirectory(dir=TESTS) as output:
            result = self.cli(url, output)
            self.assertEqual(result.returncode, 2)
            self.assertIn("所有搜索请求均失败", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(list(Path(output).iterdir()), [])
            self.assertEqual(sum(r["path"].endswith("/feeds/search") for r in requests), 2)

    def test_empty_search_exports_an_honest_empty_report(self):
        with local_source(scenario()) as (url, requests), tempfile.TemporaryDirectory(dir=TESTS) as output:
            result = self.cli(url, output)
            self.assertEqual(result.returncode, 3, result.stderr)
            paths = json.loads(result.stdout)
            report = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
            markdown = Path(paths["markdown"]).read_text(encoding="utf-8")
            self.assertEqual(report["notes"], [])
            self.assertFalse(report["partial"])
            self.assertEqual(report["summary"]["searches_succeeded"], 2)
            self.assertIn("不能据此断言平台没有相关热点", markdown)
            self.assertFalse(any(r["path"].endswith("/feeds/detail") for r in requests))

    def test_day_window_filters(self):
        for days, expected in ((1, "一天内"), (7, "一周内"), (30, "半年内"), (180, "半年内")):
            with self.subTest(days=days), local_source(scenario()) as (url, requests):
                scout.collect(scout.Client(url, token=""), ["虚构关键词"], days, 10, 30, now=FIXED_NOW)
                searches = [r for r in requests if r["path"].endswith("/feeds/search")]
                self.assertEqual(len(searches), 2)
                self.assertTrue(all(r["body"]["filters"]["publish_time"] == expected for r in searches))

    def test_detail_budget_reports_uninspected_notes(self):
        feeds = [fictional_feed(name) for name in ("限额甲", "限额乙", "限额丙")]
        details = {feed["id"]: fictional_detail(feed["id"].removeprefix("fixture-fictional-"), FIXED_NOW.isoformat()) for feed in feeds}
        with local_source(scenario(feeds, details)) as (url, requests):
            report = scout.collect(scout.Client(url, token=""), ["虚构关键词"], 7, 10, 1, now=FIXED_NOW)
        self.assertTrue(report["partial"])
        self.assertEqual(report["summary"]["not_inspected"], 2)
        self.assertEqual(sum(r["path"].endswith("/feeds/detail") for r in requests), 1)


class ScoutOfflineTests(unittest.TestCase):
    def test_abbreviated_url_cannot_override_managed_connection(self):
        for command in (["check"], ["search", "--keywords", "AI"]):
            for flag in ("--u", "--ur", "--ur=https://invalid.example"):
                args = command + ([flag] if "=" in flag else [flag, "https://invalid.example"])
                with self.subTest(args=args), mock.patch.object(scout, "Client") as client, contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        scout.main(args)
                    self.assertEqual(caught.exception.code, 2)
                    client.assert_not_called()

    def test_missing_and_invalid_metrics_stay_unknown(self):
        for value in (None, "", "未取得", "--", -1, float("nan"), True):
            with self.subTest(value=value):
                self.assertIsNone(scout.count_value(value))
        self.assertEqual(scout.count_value(0), 0)
        self.assertEqual(scout.count_value("0"), 0)
        self.assertEqual(scout.count_value("1.2万"), 12000)
        self.assertEqual(scout.count_value("2.5k+"), 2500)
        self.assertIsNone(scout.sample_score({}))
        self.assertIsNone(scout.sample_score({"likes": 99999999, "saves": None, "comments": 1}))
        self.assertEqual(scout.sample_score({"likes": 0, "saves": 0, "comments": 0}), 0)

    def test_nonpositive_timestamps_mean_unknown_not_epoch_publication(self):
        for value in (0, 0.0, "0", -1, -1000, "-1"):
            with self.subTest(value=value):
                self.assertIsNone(scout.date_value(value))

    def test_sample_never_opens_a_network_connection_and_is_clearly_labeled(self):
        with tempfile.TemporaryDirectory(dir=TESTS) as output, mock.patch.object(
                scout.urllib.request, "urlopen", side_effect=AssertionError("sample must never use the network")) as urlopen, contextlib.redirect_stdout(io.StringIO()) as stdout:
            result = scout.main(["sample", "--output-dir", output])
            self.assertEqual(result, 0)
            urlopen.assert_not_called()
            paths = json.loads(stdout.getvalue())
            report = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
            markdown = Path(paths["markdown"]).read_text(encoding="utf-8")
            self.assertTrue(paths["demo"])
            self.assertTrue(report["demo"])
            self.assertTrue(Path(paths["json"]).name.startswith("DEMO-"))
            self.assertIn("演示数据，非实时搜索结果", markdown[:150])
            self.assertIn("所有笔记均为虚构", markdown[:150])
            self.assertIn("【演示】", markdown)
            self.assertEqual(report["summary"]["searches_requested"], 0)
            self.assertTrue(all(note["url"] == "" for note in report["notes"]))
            self.assertNotIn("https://www.xiaohongshu.com/", markdown)

    def test_mutating_or_unrecognized_routes_are_blocked_before_network(self):
        client = scout.Client("http://127.0.0.1:1", token="")
        rejected = [("POST", "/publish"), ("POST", "/feeds/publish"),
                    ("POST", "/feeds/comment"), ("POST", "/feeds/like"),
                    ("DELETE", "/feeds/detail"), ("GET", "/feeds/search"),
                    ("POST", "/feeds/search?operation=publish")]
        with mock.patch.object(scout.urllib.request, "urlopen", side_effect=AssertionError("blocked routes must not connect")) as urlopen:
            for method, route in rejected:
                with self.subTest(method=method, route=route), self.assertRaises(scout.SourceError):
                    client.call(method, route, {})
            urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
