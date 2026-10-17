# lin-tools 功能入口

根据用户请求选择模块，不要默认安装两个模块：

- **小红书选题研究**：当用户明确要求安装、配置或启用这项能力时，读取并执行 [START.md](START.md)；英文请求使用 [START.en.md](START.en.md)。这是面向能运行工具的机器人的安装流程；不要只回复安装教程，也不要把文件下载成功说成已经接通账号。
- **LiveCanvas 安装或制作 Live 图片**：先读 [模块说明](skills/livecanvas/README.md)，再读 [实际技能](skills/livecanvas/SKILL.md)，按其中的环境要求和流程处理。不要套用小红书研究模块的安装流程。
- 请求只说安装本项目、且上下文无法判断模块时，先确认要使用的模块。

普通代码审查、仓库推荐和文件阅读不触发安装。修改小红书研究模块时保持其只读研究范围，验证脚本的真实行为，并在 VALIDATION.md 区分本地测试、产品内配置和真实账号搜索。LiveCanvas 的制作与验证按其模块文档执行。

## English

Choose the module requested by the user; do not install both by default:

- **Xiaohongshu topic research:** When the user explicitly requests installation, configuration, or activation of this capability, read and follow [START.en.md](START.en.md). This workflow is for a bot that can execute tools. Do not merely return an installation tutorial or describe downloaded files as a connected account.
- **Installing LiveCanvas or creating Live Photos:** Read the [module guide](skills/livecanvas/README.en.md), then the [skill](skills/livecanvas/SKILL.md), and follow their environment requirements and workflow. Do not use the Xiaohongshu research module's installation workflow.
- If the user only asks to install this project and the context does not identify a module, clarify which module they want.

Ordinary code review, repository recommendations, and file reading do not trigger installation. Keep changes to the Xiaohongshu research module within its read-only research scope, verify actual script behavior, and distinguish local tests, in-product configuration, and real account searches in VALIDATION.md and [VALIDATION.en.md](VALIDATION.en.md). Follow LiveCanvas's module documentation for production and validation.
