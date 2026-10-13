#!/usr/bin/env python3
"""Read-only Xiaohongshu research collector. Python 3.9+, standard library only."""
import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

TZ = dt.timezone(dt.timedelta(hours=8))
READ_ROUTES = {("GET", "/login/status"), ("POST", "/feeds/search"), ("POST", "/feeds/detail")}


class SourceError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, url=None, token=None):
        raw = (url or os.environ.get("XHS_MCP_URL") or "http://127.0.0.1:18060").rstrip("/")
        parts = urllib.parse.urlsplit(raw)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise SourceError("XHS_MCP_URL 必须是无账号密码、查询参数的 HTTP/HTTPS 服务地址。")
        path = parts.path.rstrip("/")
        if path.endswith("/mcp"):
            path = path[:-4]
        if not path.endswith("/api/v1"):
            path += "/api/v1"
        self.base = urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, "", ""))
        self.token = token if token is not None else os.environ.get("XHS_MCP_TOKEN", "")
        self.opener = urllib.request.build_opener(NoRedirect())

    def call(self, method, route, body=None):
        if (method, route) not in READ_ROUTES:
            raise SourceError("该机器人只允许登录状态检查、搜索和读取详情。")
        headers = {"Accept": "application/json", "User-Agent": "xhs-topic-scout/1.0"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + route, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=60) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            raise SourceError("上游返回 HTTP %s；请检查服务、鉴权及登录状态。" % exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise SourceError("无法连接小红书数据服务或请求超时；请确认服务已启动且此运行环境可以访问。") from None
        except (ValueError, UnicodeError):
            raise SourceError("上游未返回有效 JSON。") from None
        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise SourceError("上游报告失败；请在服务端检查登录状态或访问限制。")
        return payload.get("data")


def count_value(value):
    """None means unknown; never silently turn missing metrics into zero."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if math.isfinite(value) and value >= 0 else None
    text = str(value).strip().replace(",", "").replace("，", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([万千亿wWkK]?)\+?", text)
    if not match:
        return None
    multiplier = {"万": 10000, "w": 10000, "千": 1000, "k": 1000, "亿": 100000000}.get(match[2].lower(), 1)
    return int(float(match[1]) * multiplier)


def date_value(value):
    try:
        if value is None or isinstance(value, bool) or value == "":
            return None
        if isinstance(value, (int, float)) or str(value).isdigit():
            number = float(value)
            if number <= 0:
                return None
            if number > 100000000000:
                number /= 1000
            return dt.datetime.fromtimestamp(number, TZ)
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=TZ) if parsed.tzinfo is None else parsed.astimezone(TZ)
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def sample_score(metrics):
    weights = {"likes": 1, "saves": 1.5, "comments": 2}
    known = [(weights[key], count_value(metrics.get(key))) for key in weights]
    if any(value is None for _, value in known):
        return None
    return round(sum(weight * math.log10(1 + value) for weight, value in known if value is not None), 3)


def normalize(feed, detail, keywords, now, days):
    card = feed.get("noteCard") or {}
    container = detail.get("data") or {}
    note = container.get("note") or {}
    note_id = str(note.get("noteId") or feed.get("id") or "")
    published = date_value(note.get("time"))
    earliest = now - dt.timedelta(days=days)
    status = "unknown" if published is None else ("future" if published > now else ("in_window" if published >= earliest else "outside_window"))
    source_metrics = note.get("interactInfo") or card.get("interactInfo") or {}
    metrics = {name: source_metrics.get(key) if source_metrics.get(key) not in (None, "") else None for name, key in (("likes", "likedCount"), ("saves", "collectedCount"), ("comments", "commentCount"))}
    parsed_metrics = {key: count_value(value) for key, value in metrics.items()}
    token = feed.get("xsecToken") or ""
    url = "https://www.xiaohongshu.com/explore/" + urllib.parse.quote(note_id, safe="")
    if token:
        url += "?" + urllib.parse.urlencode({"xsec_token": token, "xsec_source": "pc_search"})
    comments_container = container.get("comments") or {}
    comment_items = comments_container.get("list") or []
    excerpts = [str(item["content"])[:400] for item in comment_items[:5] if isinstance(item, dict) and item.get("content")]
    user = note.get("user") or card.get("user") or {}
    return {
        "id": note_id, "title": str(note.get("title") or card.get("displayTitle") or "无标题"),
        "author": str(user.get("nickname") or user.get("nickName") or "未取得"),
        "author_id": str(user.get("userId") or ""), "url": url, "keywords": keywords,
        "published_at": published.isoformat() if published else None, "date_status": status,
        "metrics": parsed_metrics, "metrics_display": metrics,
        "metrics_complete": all(value is not None for value in parsed_metrics.values()),
        "sample_score": sample_score(metrics), "description": str(note.get("desc") or "")[:3000],
        "comment_excerpts": excerpts, "comments_read": len(excerpts),
    }


def collect(client, keywords, days, top, detail_limit, now=None, progress=None):
    now = now or dt.datetime.now(TZ)
    state = client.call("GET", "/login/status")
    if not isinstance(state, dict) or state.get("is_logged_in") is not True:
        raise SourceError("小红书尚未登录。请用上游登录工具完成登录，再运行本机器人。")
    errors, batches = [], []
    publish_time = "一天内" if days == 1 else ("一周内" if days <= 7 else "半年内")
    for keyword in keywords:
        for sort_by in ("最新", "最多收藏"):
            if progress:
                progress("正在搜索：%s（%s）" % (keyword, sort_by))
            try:
                result = client.call("POST", "/feeds/search", {"keyword": keyword, "filters": {"sort_by": sort_by, "publish_time": publish_time}})
                if not isinstance(result, dict) or not isinstance(result.get("feeds"), list):
                    raise SourceError("搜索响应结构不符合预期。")
                batches.append((keyword, result["feeds"]))
            except SourceError as exc:
                errors.append({"stage": "search", "keyword": keyword, "sort": sort_by, "error": str(exc)})
    if not batches:
        raise SourceError("所有搜索请求均失败；没有生成真实热点报告。")
    # Round-robin prevents the first keyword from consuming the entire detail budget.
    unique = {}
    for offset in range(max((len(batch) for _, batch in batches), default=0)):
        for keyword, batch in batches:
            if offset >= len(batch):
                continue
            feed = batch[offset]
            if not isinstance(feed, dict) or feed.get("modelType") != "note" or not feed.get("id"):
                continue
            note_id = str(feed["id"])
            if note_id not in unique:
                unique[note_id] = {"feed": feed, "keywords": []}
            if keyword not in unique[note_id]["keywords"]:
                unique[note_id]["keywords"].append(keyword)
    notes, excluded = [], []
    selected = list(unique.values())[:detail_limit]
    for index, item in enumerate(selected, 1):
        feed = item["feed"]
        if progress:
            progress("正在核验笔记日期与详情：%s/%s" % (index, len(selected)))
        try:
            if not feed.get("xsecToken"):
                raise SourceError("搜索结果缺少详情读取参数。")
            detail = client.call("POST", "/feeds/detail", {"feed_id": feed["id"], "xsec_token": feed["xsecToken"], "load_all_comments": False})
            if not isinstance(detail, dict) or not isinstance(detail.get("data"), dict) or not isinstance(detail["data"].get("note"), dict):
                raise SourceError("详情响应缺少 note。")
            if detail["data"]["note"].get("noteId") and str(detail["data"]["note"]["noteId"]) != str(feed["id"]):
                raise SourceError("详情笔记 ID 与搜索结果不符，已跳过以免引用错误。")
            note = normalize(feed, detail, item["keywords"], now, days)
            (notes if note["date_status"] == "in_window" else excluded).append(note)
        except SourceError as exc:
            errors.append({"stage": "detail", "note_id": str(feed["id"]), "error": str(exc)})
    notes.sort(key=lambda n: (n["sample_score"] if n["sample_score"] is not None else -1, n["published_at"]), reverse=True)
    return {
        "schema_version": 1, "demo": False, "collected_at": now.isoformat(),
        "window_start": (now - dt.timedelta(days=days)).isoformat(), "keywords": keywords, "days": days,
        "scope": "仅本次关键词搜索取得的样本，不是小红书全站热榜；单次采样不能证明增长趋势。",
        "ranking": "样本互动分 = log10(1+点赞) + 1.5×log10(1+收藏) + 2×log10(1+评论)。缺任一指标不计算分数，单列为待核实线索；万/千/+等显示值为近似值。",
        "summary": {"searches_succeeded": len(batches), "searches_requested": len(keywords) * 2,
                    "unique_search_notes": len(unique), "detail_attempts": len(selected),
                    "not_inspected": max(0, len(unique) - len(selected)), "in_window": len(notes),
                    "excluded_by_date": len(excluded), "errors": len(errors)},
        "top": top, "notes": notes, "excluded_notes": excluded, "errors": errors,
        "partial": bool(errors or len(unique) > len(selected) or any(n["date_status"] in ("unknown", "future") for n in excluded) or any(not n["metrics_complete"] for n in notes)),
    }


def md(value):
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;").replace("[", "\\[").replace("]", "\\]")


def render(report):
    demo = report.get("demo", False)
    title = "小红书热点研究素材"
    lines = ["# " + title, ""]
    if demo:
        lines += ["**演示数据，非实时搜索结果。所有笔记均为虚构，不可作为选题证据。**", ""]
    lines += ["采集时间：" + report["collected_at"], "", "关键词：" + "、".join(md(k) for k in report["keywords"]),
              "", "时间范围：" + report["window_start"] + " 至 " + report["collected_at"], "", report["scope"], ""]
    s = report["summary"]
    lines += ["去重取得 %s 篇；尝试核验 %s 篇；确认在时间范围内 %s 篇；未检查 %s 篇；日期排除 %s 篇；请求失败 %s 次。" % (s["unique_search_notes"], s["detail_attempts"], s["in_window"], s["not_inspected"], s["excluded_by_date"], s["errors"]), ""]
    if report.get("partial"):
        lines += ["**本次为部分采样结果；请结合下方数据缺口阅读。**", ""]
    ranked = [n for n in report["notes"] if n["sample_score"] is not None]
    incomplete = [n for n in report["notes"] if n["sample_score"] is None]
    shown = ranked[:report["top"]] + incomplete[:report["top"]]
    lines += ["## 候选笔记（完整指标样本）", "", "| 标题 / 来源 | 发布时间 | 点赞 | 收藏 | 评论 | 样本互动分 |", "|---|---|---:|---:|---:|---:|"]
    for note in ranked[:report["top"]]:
        name = ("【演示】" if demo else "") + note["title"]
        label = md(name) if demo else "[" + md(name) + "](" + note["url"] + ")"
        values = [md(note["metrics_display"].get(k) if note["metrics_display"].get(k) is not None else "未取得") for k in ("likes", "saves", "comments")]
        score = str(note["sample_score"]) if note["sample_score"] is not None else "无法计算"
        if not note["metrics_complete"]:
            score += "（指标不全）"
        lines.append("| %s | %s | %s | %s | %s | %s |" % (label, note["published_at"][:10], *values, score))
    if incomplete:
        lines += ["", "### 指标不全的待核实线索（不参加排名）", ""]
        for note in incomplete[:report["top"]]:
            label = md(note["title"]) if demo else "[" + md(note["title"]) + "](" + note["url"] + ")"
            lines.append("- %s%s；日期 %s；点赞 %s，收藏 %s，评论 %s。" % ("【演示】" if demo else "", label, note["published_at"][:10], *(md(note["metrics_display"].get(k) if note["metrics_display"].get(k) is not None else "未取得") for k in ("likes", "saves", "comments"))))
    if not report["notes"]:
        lines += ["", "没有取得可确认在指定时间内的候选笔记；不能据此断言平台没有相关热点。"]
    lines += ["", "排序说明：" + report["ranking"], "", "## 可供机器人分析的正文与评论片段", ""]
    for index, note in enumerate(shown, 1):
        lines += ["### %s. %s%s" % (index, "【演示】" if demo else "", md(note["title"])), "", "作者：" + md(note["author"]), "", "正文摘录：" + md(note["description"] or "未取得"), "", "评论片段（%s 条，仅为已读取部分）：" % note["comments_read"], ""]
        lines += ["- " + md(c) for c in note["comment_excerpts"]] or ["未读取到评论正文，不能推断评论区观点。"]
        lines += [""]
    lines += ["## 数据缺口", ""]
    for note in report["excluded_notes"]:
        lines.append("- %s：%s；未纳入近期排行。" % (md(note["title"]), {"unknown": "发布时间未确认", "future": "发布时间晚于采集时间", "outside_window": "超出时间范围"}.get(note["date_status"], note["date_status"])))
    for error in report["errors"]:
        lines.append("- %s / %s：%s" % (error["stage"], md(error.get("keyword") or error.get("note_id", "")), md(error["error"])))
    if not report["errors"] and not report["excluded_notes"]:
        lines.append("本次读取未报告错误。搜索样本仍受账号、排序、页面加载范围影响，不保证完整。")
    lines += ["", "## 下一步：归纳话题", "", "请机器人结合 JSON 中的证据，按重复出现的问题与使用场景归纳最多 5 个话题候选，每个附来源和日期。两个独立作者支持时可归为共同话题；只有一篇时标明单篇线索。提出最多 3 个原创选题角度，不复制原笔记。", ""]
    return "\n".join(lines)


def save_report(report, directory):
    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(TZ).strftime("%Y%m%d-%H%M%S-%f")
    base = root / (("DEMO-" if report.get("demo") else "xhs-") + stamp)
    json_path, md_path = base.with_suffix(".json"), base.with_suffix(".md")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render(report), encoding="utf-8")
    return {"json": str(json_path.resolve()), "markdown": str(md_path.resolve())}


def demo_report():
    now = dt.datetime(2026, 10, 14, 12, tzinfo=TZ)
    feed = {"id": "demo-fictional-note", "noteCard": {"displayTitle": "虚构示例：AI整理会议纪要"}}
    detail = {"data": {"note": {"noteId": "demo-fictional-note", "title": "虚构示例：AI整理会议纪要", "time": int((now - dt.timedelta(days=2)).timestamp() * 1000), "desc": "这是虚构测试数据，用于展示格式。", "interactInfo": {"likedCount": "120", "collectedCount": "80", "commentCount": "12"}}, "comments": {"list": [{"content": "虚构评论：能否导出待办清单？"}]}}}
    note = normalize(feed, detail, ["AI办公"], now, 7)
    note["url"] = ""
    return {"schema_version": 1, "demo": True, "collected_at": now.isoformat(), "window_start": (now - dt.timedelta(days=7)).isoformat(), "keywords": ["AI办公"], "days": 7, "scope": "仅演示报告格式，没有搜索小红书。", "ranking": "log10(1+点赞) + 1.5×log10(1+收藏) + 2×log10(1+评论)，仅比较本次样本。", "summary": {"searches_succeeded": 0, "searches_requested": 0, "unique_search_notes": 1, "detail_attempts": 0, "not_inspected": 0, "in_window": 1, "excluded_by_date": 0, "errors": 0}, "top": 10, "notes": [note], "excluded_notes": [], "errors": [], "partial": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="小红书热点侦察员：只读搜索、日期核验和研究素材导出。")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="检查数据服务和小红书登录状态")
    check.add_argument("--url", help="xiaohongshu-mcp 服务地址，也可设置 XHS_MCP_URL")
    search = sub.add_parser("search", help="采集真实搜索结果")
    search.add_argument("--keywords", nargs="+", required=True)
    search.add_argument("--days", type=int, default=7)
    search.add_argument("--top", type=int, default=10)
    search.add_argument("--detail-limit", type=int, default=30)
    search.add_argument("--url")
    search.add_argument("--output-dir", default="reports")
    sample = sub.add_parser("sample", help="生成醒目标注的虚构演示，不联网")
    sample.add_argument("--output-dir", default="reports")
    args = parser.parse_args(argv)
    try:
        if args.command == "sample":
            print(json.dumps({"demo": True, **save_report(demo_report(), args.output_dir)}, ensure_ascii=False))
            return 0
        client = Client(args.url)
        if args.command == "check":
            data = client.call("GET", "/login/status")
            logged = isinstance(data, dict) and data.get("is_logged_in") is True
            print(json.dumps({"connected": True, "logged_in": logged}, ensure_ascii=False))
            return 0 if logged else 2
        keywords = list(dict.fromkeys(k.strip() for k in args.keywords if k.strip()))
        if not 1 <= len(keywords) <= 5 or any(len(k) > 100 for k in keywords):
            parser.error("请提供 1–5 个关键词，每个不超过 100 字。")
        if not 1 <= args.days <= 180 or not 1 <= args.top <= 50 or not 1 <= args.detail_limit <= 100:
            parser.error("days 为 1–180；top 为 1–50；detail-limit 为 1–100。")
        report = collect(client, keywords, args.days, args.top, args.detail_limit, progress=lambda text: print(text, file=sys.stderr, flush=True))
        files = save_report(report, args.output_dir)
        print(json.dumps({"demo": False, "partial": report["partial"], "summary": report["summary"], **files}, ensure_ascii=False))
        return 0 if report["notes"] else 3
    except SourceError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
