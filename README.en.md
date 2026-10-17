# lin-tools | Xiaohongshu Topic Research and Live Photo Tools

[简体中文](README.md) | English

This repository contains two modules you can use as needed:

| Module | Purpose | Entry points |
| --- | --- | --- |
| Xiaohongshu topic research | Let Grok Bot search, verify, and organize evidence for content topics | [Installation and configuration](START.en.md) · [Skill](skills/xhs-topic-scout/SKILL.md) |
| LiveCanvas (实况画布) | Create Live Photos | [Module guide and installation requirements](skills/livecanvas/README.en.md) · [Skill](skills/livecanvas/SKILL.md) |

LiveCanvas comes from the open-source [pengchujin/livecanvas](https://github.com/pengchujin/livecanvas) project. This repository includes the tool for optional use; credit for the original work belongs to its upstream authors. Its main license is MIT, with components under Apache-2.0. Preserve the applicable licenses and notices when using or redistributing it. See the [LiveCanvas module guide](skills/livecanvas/README.en.md) for installation requirements and usage.

## Grok Bot Xiaohongshu Topic Scout (小红书选题机器人)

Built for **Grok Bot users**, this project provides a **Xiaohongshu (小红书 / RED) topic research skill and bot workflow**. Send Grok Bot the repository link with an installation request so it can follow the setup workflow. Once configuration and the connection have been verified, ask Grok Bot to search recent Xiaohongshu posts by field or keyword, verify publication dates, collect available engagement data and comment excerpts, and use that evidence to suggest topics and original content ideas.

**Read-only research: no publishing, commenting, liking, bookmarking, or automatic scheduling.** Results describe the current search sample, not a platform-wide trending chart.

## Install the Xiaohongshu skill in Grok Bot with one message

Send this message to your own Grok Bot:

> Install and enable the Xiaohongshu topic research capability from https://github.com/honglin0000/lin for yourself. Follow START.en.md to save your research instructions, register the skill, configure the connection, and verify a real search. Show me a QR code if I need to sign in; carry out the remaining steps yourself.

The bot should read the repository, persist its research instructions, install the complete skill, start the data service, and check the login status. If sign-in is required, it shows a QR code for you to scan with the Xiaohongshu app. Once login and a real search have been verified, you can simply say, “Find Xiaohongshu topics about AI office tools from the past week.” You do not need to copy terminal commands, enter ports, or send cookies.

This requires your Grok Bot environment to support network access, Python execution, and persistent instructions and skills. If a capability or system dependency is missing, the bot should explain the specific blocker. **“One message” describes the installation entry point; it does not mean every environment has been verified.** See the [validation record](VALIDATION.en.md) for the current status.

## Help improve the project

Ideas, issue reports, and contributions are welcome:

- **Suggest an improvement or report a problem:** [Open an issue](https://github.com/honglin0000/lin/issues/new/choose). Plain English or Chinese is fine; no coding knowledge is required.
- **Contribute a change:** Fork this repository, make changes in your copy, and open a pull request. The maintainer reviews it and decides whether to merge it.
- **Join the discussion:** [Browse existing issues](https://github.com/honglin0000/lin/issues) and share your experience.

Real installation and search feedback, data-processing fixes, topic-analysis improvements, and clearer documentation are especially useful. See [Contributing](CONTRIBUTING.en.md).

## Xiaohongshu topic research with Grok Bot

- Candidate posts from the past 1–180 days, with a default of 7 days; accept 1–5 keywords per request.
- Two searches for each keyword: newest (最新) and most saved (最多收藏), deduplicated by post ID.
- Publication dates verified from post details, excluding out-of-range posts, unknown dates, and anomalous future dates.
- Reports with source links, dates, displayed like/save/comment counts, post text, and the comment excerpts actually read.
- Up to 5 candidate topics and 3 original content directions, synthesized by Grok Bot from the collected evidence.

## Use with Grok Bot

The full installation workflow is in [START.en.md](START.en.md), the bot's research instructions are in [PROFILE.en.md](PROFILE.en.md), and the English skill reference is in [skills/xhs-topic-scout/SKILL.en.md](skills/xhs-topic-scout/SKILL.en.md). The existing [SKILL.md](skills/xhs-topic-scout/SKILL.md) remains the registration entry point for the same skill. Install the entire skill directory; the English reference does not create a separate skill or duplicate the scripts. By default, add this capability to the current bot while keeping its name, existing responsibilities, and other skills. Create a new bot only when the user explicitly requests one.

The skill's `scripts/setup.py` manages the required data service: it downloads and verifies a pinned release, saves private connection settings, starts the service in the same environment, checks login, and generates a QR image when needed. Later searches reuse the saved settings and attempt to restart a stopped service. This script does not replace Grok Bot's native mechanisms for persisting instructions or registering skills; the bot must perform those steps and read them back as described in START.en.md.

Data comes from the open-source [xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp) project. The setup helper supports Linux x86_64 and Apple Silicon Macs. It uses the pinned v2.5.5 release with verified download checksums and exits explicitly on unsupported platforms. The upstream service downloads a browser on first launch. Missing system libraries are reported; the helper does not elevate privileges to install them. This repository does not include upstream binaries, accounts, or login credentials.

Services created by the helper run on the same machine as the search script, listen only on the loopback address, and require authentication. `127.0.0.1` inside a Grok Bot cloud computer does not point to your Mac. The helper does not expose public ports or create tunnels. Each user has their own private settings and Xiaohongshu login session.

## What to ask Grok Bot after installation

> Research Xiaohongshu topics from the past week for “AI办公”, “会议纪要”, and “自动做PPT”. Search and verify the evidence first, then give me 5 candidate topics with sources and 3 original content ideas. Return fewer items if the evidence is insufficient.

Those example keywords mean AI office tools, meeting notes, and automatic presentation creation. You can also research travel, home decor, fashion, learning, or other fields. If no field can be inferred, the bot asks for keywords.

These English documents cover installation and use. The current command-line diagnostics and generated report labels remain in Chinese; JSON keys and command options are unchanged. Grok Bot can explain the evidence in the user's preferred language.

## Run locally

The following commands are for bots and developers. Ordinary users only need the message above. Python 3.9 or later is required; no additional Python packages are needed.

```bash
python3 skills/xhs-topic-scout/scripts/setup.py ensure
python3 skills/xhs-topic-scout/scripts/setup.py login
python3 skills/xhs-topic-scout/scripts/setup.py status
python3 skills/xhs-topic-scout/scripts/setup.py run search --keywords "AI办公" "会议纪要" --days 7 --top 10
```

`ensure` installs/starts the service and checks its status. `login` saves a private QR image when not signed in. `status` only reads the status. `run` prepares the connection automatically and executes the collection script. `needs_login` means the user must scan the code; it does not mean installation is complete or a search has succeeded. Generate a new code after expiry and check the status after scanning.

Setup-helper exit codes: `0` means the service and login are ready; `3` means login is needed or the service is not running; `2` means configuration failed. Once `run` starts collection, it uses the collection script's exit codes described below. Automation must also inspect the JSON status; an exit code alone does not establish that real topic results were obtained.

The private runtime directory defaults to `~/.local/share/xhs-topic-scout`; override it with `XHS_SCOUT_HOME` if needed. The helper does not print tokens, cookies, or raw QR-code data to the user, and it does not create startup items or scheduled tasks.

If you already operate a data service, you can use the collection script directly:

```bash
python3 skills/xhs-topic-scout/scripts/scout.py check
python3 skills/xhs-topic-scout/scripts/scout.py search --keywords "AI办公" "会议纪要" --days 7 --top 10
```

The default service URL is `http://127.0.0.1:18060`. Set a different URL with the `XHS_MCP_URL` environment variable or `--url`; trailing `/mcp` or `/api/v1` paths are recognized. When upstream `AUTH_TOKEN` is enabled, set the corresponding `XHS_MCP_TOKEN` in the execution environment. Do not put credentials in the repository, chat, or command arguments.

Results are saved in `reports/` as both JSON and Markdown. Filenames include a timestamp and do not overwrite earlier runs. At most 30 post details are read by default; `--detail-limit` accepts 1–100. Each result records how many posts were not checked, failed requests, and exclusions based on dates. Reports may contain post access parameters and are excluded from Git by default.

The script produces **candidate posts and evidence**. Grok Bot groups topics and suggests original content according to the skill; no additional model API is required.

## Ranking and limitations

Sample engagement score: `log10(1 + likes) + 1.5 × log10(1 + saves) + 2 × log10(1 + comments)`.

This is a transparent ranking rule for the sample, not the platform's algorithm. Missing metrics remain “not obtained” rather than zero. If any metric is missing, no score is calculated and the post appears separately as a lead to verify. Complete-metric candidates and incomplete-metric leads each show up to `--top` items. Original displayed values such as `1.7万` (about 17,000) and `10万+` (100,000+) are preserved; converted values are only used for approximate ranking.

The upstream service returns only search results already loaded on the page. Results can depend on the signed-in account and selected sort order. Even when the search filter says “within one week,” the script checks the date in each post's details. A single collection cannot establish that interest is “rising” or “exploding.” The bot must not draw conclusions about comments it has not read.

## Validation

```bash
python3 -m unittest discover -s tests -v
python3 skills/xhs-topic-scout/scripts/scout.py sample --output-dir reports
```

`sample` runs entirely offline. Its output is labeled “演示数据，非实时搜索结果” (“Demo data, not live search results”) and only demonstrates the report format. Collection-script exit codes: `0` means complete (inspect `partial` to detect partial success); `2` means a service, login, or argument error; `3` means no posts were verified within the requested time window.

See [VALIDATION.en.md](VALIDATION.en.md) for completed checks and remaining verification. The repository does not include real accounts, cookies, API keys, or real collected reports.

## Upstream references

The HTTP integration was checked against `xpzouying/xiaohongshu-mcp` commit `7797fd375aba02dcd33afe143f6bee13e5870859`: [API documentation](https://github.com/xpzouying/xiaohongshu-mcp/blob/7797fd375aba02dcd33afe143f6bee13e5870859/docs/API.md) and [search implementation](https://github.com/xpzouying/xiaohongshu-mcp/blob/7797fd375aba02dcd33afe143f6bee13e5870859/xiaohongshu/search.go). This project independently implements its collection logic and connects through public interfaces; it does not copy upstream code.
