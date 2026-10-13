# Grok Bot 小红书选题机器人｜小红书热点侦察员

简体中文 | [English](README.en.md)

本项目主要面向 **Grok Bot 用户**，提供**小红书选题研究技能和机器人工作流**。把仓库链接与安装请求发给 Grok Bot，让它按安装流程配置这项能力；完成配置并验证连接后，可让 Grok Bot 按领域或关键词搜索近期小红书笔记、核验日期、整理可获取的互动数据与评论片段，再归纳值得关注的话题与原创选题。

**只读研究，不包含发笔记、评论、点赞、收藏或自动排期。** 输出代表本次搜索样本，不是小红书全站热榜。

## 在 Grok Bot 中一句话安装小红书技能

把下面这一句话发给你自己的 Grok Bot：

> 请给自己装好这个项目里的小红书热点研究功能，按 START.md 自动配置职责、技能和连接，并检查能否正常使用：https://github.com/honglin0000/lin

机器人应自行读取仓库、记住研究职责、安装完整技能、启动数据服务并检查登录。需要登录时，它会出示二维码，你用小红书 App 扫码；登录状态和一次真实搜索验证通过后，即可直接说“帮我找最近一周 AI 办公的话题”。不需要客户复制终端命令、填写端口或传送 Cookie。

这依赖 Grok Bot 实际具备联网、运行 Python 和保存技能/职责的能力；缺少能力或系统依赖时会说明卡在哪一步。**“一句话”是安装入口，不表示任何环境都已验证可用。** 当前验证情况见 [验证记录](VALIDATION.md)。

## 欢迎一起完善

有想法、发现问题，或者愿意改进机器人，都欢迎参与：

- **提建议 / 反馈问题**：[新建 Issue](https://github.com/honglin0000/lin/issues/new/choose)，用中文描述即可，不需要会写代码。
- **提交修改**：Fork 本仓库，在自己的副本中修改，再向本仓库提交 Pull Request（修改提案）。由仓库维护者查看并决定是否合并。
- **参与讨论**：[查看已有建议](https://github.com/honglin0000/lin/issues)，补充你的使用体验。

优先欢迎真实安装与搜索反馈、数据处理修复、话题分析方法和中文说明改进。具体步骤见 [参与说明](CONTRIBUTING.md)。

## Grok Bot 的小红书研究功能

- 最近 1–180 天的候选笔记，默认 7 天；每次输入 1–5 个关键词。
- 每个关键词分别搜索「最新」「最多收藏」，按笔记 ID 去重。
- 从笔记详情确认发布时间，排除过期、日期不明和异常未来时间的笔记。
- 带来源链接、日期、点赞/收藏/评论显示值、正文及已读取评论片段的报告。
- Grok Bot 根据这些证据归纳最多 5 个话题候选，再给最多 3 个原创选题方向。

## 给 Grok Bot 使用

完整安装流程在 [START.md](START.md)，机器人职责在 [PROFILE.md](PROFILE.md)，实际技能在 [skills/xhs-topic-scout/SKILL.md](skills/xhs-topic-scout/SKILL.md)。默认给当前机器人增加这项能力，保留它已有的名称、职责和其他技能；用户明确要求新建时才新建。

技能目录下的 `scripts/setup.py` 自动处理本项目需要的数据服务：下载并校验固定版本、保存私有连接配置、在同一环境启动服务、检查登录并生成扫码图片。后续搜索自动复用配置，服务停止时尝试重新启动。它不替代 Grok Bot 原生的职责保存和技能注册，后两项由机器人按 START.md 执行并回读验证。

数据来自开源 [xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp)。安装助手支持 Linux x86_64 和 Apple Silicon Mac，固定使用已核实下载校验值的 v2.5.5；其他平台会明确退出。首次启动由上游下载浏览器；缺少系统运行库时说明原因，不自动提权安装软件。仓库不附带上游安装包、账号或登录凭据。

安装助手新建的服务与搜索脚本放在同一台电脑，只监听回环地址并使用鉴权。Grok Bot 云电脑的 `127.0.0.1` 不会指向你的 Mac；安装助手不会开放公网端口或创建隧道。每位客户使用自己的私有配置和小红书登录状态。

## 装好后这样对 Grok Bot 说

> 帮我研究最近一周小红书上“AI办公”“会议纪要”“自动做PPT”的话题。先搜索和核验，再给我 5 个有来源的候选话题，以及 3 个原创选题方向。缺少证据时不要凑数。

也可以换成旅行、家居、穿搭、学习等领域。未指定领域时，机器人会先问关键词。

## 本地运行

以下命令供机器人和开发者使用，普通用户只需上面的一句话。需要 Python 3.9 或更高版本，无额外 Python 依赖。

```bash
python3 skills/xhs-topic-scout/scripts/setup.py ensure
python3 skills/xhs-topic-scout/scripts/setup.py login
python3 skills/xhs-topic-scout/scripts/setup.py status
python3 skills/xhs-topic-scout/scripts/setup.py run search --keywords "AI办公" "会议纪要" --days 7 --top 10
```

`ensure` 安装/启动并检查；`login` 在未登录时保存私有二维码图片；`status` 只查看状态；`run` 自动准备连接并执行采集脚本。`needs_login` 表示等待扫码，不是安装完成或搜索成功。二维码过期后重新生成，扫码后再检查状态。

安装助手返回码：`0` 服务与登录就绪，`3` 等待登录或服务未运行，`2` 配置失败；`run` 开始采集后沿用下文采集脚本的返回码。自动流程应同时检查 JSON 的状态，不能只根据返回码判断是否有真实话题结果。

私有运行目录默认在 `~/.local/share/xhs-topic-scout`，可用 `XHS_SCOUT_HOME` 指定。安装助手不向用户打印令牌、Cookie 或二维码原始数据；不创建开机启动或定时任务。

如果已经自行部署了数据服务，也可直接使用原有采集脚本：

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
