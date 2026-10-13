# 小红书热点侦察员

给 Grok Bot 使用的小红书话题研究机器人：输入领域或关键词，搜索近期笔记，核验日期，整理互动数据和评论，再由机器人归纳值得关注的话题与原创选题。

**只读研究，不包含发笔记、评论、点赞、收藏或自动排期。** 输出代表本次搜索样本，不是小红书全站热榜。

## 欢迎一起完善

有想法、发现问题，或者愿意改进机器人，都欢迎参与：

- **提建议 / 反馈问题**：[新建 Issue](https://github.com/honglin0000/lin/issues/new/choose)，用中文描述即可，不需要会写代码。
- **提交修改**：Fork 本仓库，在自己的副本中修改，再向本仓库提交 Pull Request（修改提案）。由仓库维护者查看并决定是否合并。
- **参与讨论**：[查看已有建议](https://github.com/honglin0000/lin/issues)，补充你的使用体验。

优先欢迎真实安装与搜索反馈、数据处理修复、话题分析方法和中文说明改进。具体步骤见 [参与说明](CONTRIBUTING.md)。

## 能得到什么

- 最近 1–180 天的候选笔记，默认 7 天；每次输入 1–5 个关键词。
- 每个关键词分别搜索「最新」「最多收藏」，按笔记 ID 去重。
- 从笔记详情确认发布时间，排除过期、日期不明和异常未来时间的笔记。
- 带来源链接、日期、点赞/收藏/评论显示值、正文及已读取评论片段的报告。
- Grok Bot 根据这些证据归纳最多 5 个话题候选，再给最多 3 个原创选题方向。

## 给 Grok Bot 使用

把本仓库地址交给 Grok Bot，并发送：

> 请读取这个仓库的 START.md，按其中说明创建“小红书热点侦察员”，安装随附的 xhs-topic-scout 技能和脚本。完成后检查数据服务是否能连接、是否已登录。没有连接成功就告诉我具体缺什么，不要用演示数据代替。暂不创建定时任务。

机器人职责在 [PROFILE.md](PROFILE.md)，实际技能在 [skills/xhs-topic-scout/SKILL.md](skills/xhs-topic-scout/SKILL.md)。Grok Bot 的技能安装能力与账号版本有关；这些文件不是官方一键导入包，导入后需要验证。

**第一次接入需要小红书数据服务与登录。** 本项目连接开源 [xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp)，不包含它的安装包、浏览器、账号或登录凭据。可运行在该服务旁边，也可连接你配置的可达服务地址。

Grok Bot 的云端电脑和你的 Mac 是两个运行环境。若服务装在 Mac 上，云端的 `127.0.0.1` 不会指向 Mac；必须先解决两端连接，或在同一环境运行采集脚本。不要为了接入而把未鉴权的账号操作服务直接暴露到公网。

## 装好后这样说

> 帮我研究最近一周小红书上“AI办公”“会议纪要”“自动做PPT”的话题。先搜索和核验，再给我 5 个有来源的候选话题，以及 3 个原创选题方向。缺少证据时不要凑数。

也可以换成旅行、家居、穿搭、学习等领域。未指定领域时，机器人会先问关键词。

## 本地运行

需要 Python 3.9 或更高版本，无额外 Python 依赖。先按上游说明启动服务并完成小红书登录，再运行：

```bash
python3 skills/xhs-topic-scout/scripts/scout.py check
python3 skills/xhs-topic-scout/scripts/scout.py search --keywords "AI办公" "会议纪要" --days 7 --top 10
```

默认数据服务为 `http://127.0.0.1:18060`。可通过 `XHS_MCP_URL` 环境变量或 `--url` 设置服务地址；地址末尾的 `/mcp` 或 `/api/v1` 均可识别。上游启用 `AUTH_TOKEN` 时，在运行环境设置对应的 `XHS_MCP_TOKEN`；不要把密钥写进仓库、聊天或命令参数。

结果保存在 `reports/`，同次运行有 JSON 和 Markdown 两份，文件名带时间且不会覆盖前次结果。默认最多读取 30 篇详情，可用 `--detail-limit` 调整到 1–100。每次结果会说明未检查数量、失败请求和日期排除情况。报告可能带笔记访问参数，已默认排除在 Git 上传之外。

脚本提供**候选笔记和证据**；话题归类及选题建议由 Grok Bot 按技能完成，不需要另接一个模型 API。

## 排序与局限

样本互动分：`log10(1+点赞) + 1.5×log10(1+收藏) + 2×log10(1+评论)`。

这是公开、可解释的样本排序规则，不是平台算法。缺失指标保留为「未取得」，不当成零；缺少任一指标时不计算分数，单列为待核实线索。完整指标候选与待核实线索各展示最多 `--top` 条。`1.7万`、`10万+` 等原始显示值会保留，换算值仅用于近似排序。

上游只返回页面已加载的搜索结果，可能受登录账号和搜索排序影响。即使筛选器写着「一周内」，也会逐篇核验详情日期。只采集一次不能证明「热度上涨」「爆发增长」。未读取评论正文时不会生成评论区结论。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 skills/xhs-topic-scout/scripts/scout.py sample --output-dir reports
```

`sample` 完全不联网，输出标明「演示数据，非实时搜索结果」，只能查看格式。退出码：`0` 完成（查看输出中的 `partial` 判断是否部分成功）；`2` 服务/登录/参数错误；`3` 没有核验出指定时间内的笔记。

请查看 [VALIDATION.md](VALIDATION.md) 了解本次已完成和未完成的验证。仓库不附带真实账号、Cookie、API 密钥或真实采集报告。

## 上游依据

HTTP 接口按 `xpzouying/xiaohongshu-mcp` 的提交 `7797fd375aba02dcd33afe143f6bee13e5870859` 核对：[API 文档](https://github.com/xpzouying/xiaohongshu-mcp/blob/7797fd375aba02dcd33afe143f6bee13e5870859/docs/API.md)、[搜索实现](https://github.com/xpzouying/xiaohongshu-mcp/blob/7797fd375aba02dcd33afe143f6bee13e5870859/xiaohongshu/search.go)。本项目独立编写采集逻辑，通过公开接口连接上游；没有复制上游代码。
