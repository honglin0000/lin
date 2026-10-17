# LiveCanvas 收录验证 / Import validation

验证日期：2026-10-17（Asia/Shanghai）。这是 lin-tools 本次收录的本地验证记录，不代表全部设备或接收平台均已通过。

## 已通过

- 上游版本 `168e1461059105d091ba0df666703c63ccbaaa5c` 的 26 个文件完整收录，逐文件字节一致；主 MIT 许可、便携组件 Apache-2.0 LICENSE 与 NOTICE 均保留。
- 新入口及技能内本地 Markdown 引用存在；Python 语法和 JSON 文件可解析。
- Skills CLI 的只列出模式识别到 `livecanvas` 和原有 `xhs-topic-scout`，没有安装技能。
- 合成示例数据的结构校验通过；不表示真实事实校验。
- macOS 原生路径：使用本目录未修改的 `pair_live_photo.swift` 编译运行，2 秒、30 fps、320×240、无声 H.264 与同源 JPEG 在 1 秒处配对；标识和时间元数据读回、本机 PHLivePhoto 加载及 `.pvt` 封装通过，包内照片和视频哈希与配对资源一致。未导入照片库。
- 原有小红书研究模块的 41 项本地测试通过；未重新登录或进行真实搜索。

## 便携 Python 路径的已知问题

本次组合为 macOS、Python 3.12.14、Pillow 11.3.0、imageio-ffmpeg 0.6.0 附带的完整 FFmpeg 7.1，以及 Remotion 4.0.530 附带的 ffprobe n7.1。运行上游的 4 个测试方法，2 个通过、2 个出现错误，共 3 条错误记录：封面时间为 1 秒和 59/30 秒的两个子测试，以及损坏检测测试的准备阶段，均停在 `pair_live_photo.py` 读取元数据包 `duration_time` 时，该字段未出现在当前 ffprobe 输出中。

因此，本次不将便携路径记为全部通过，也不推断所有 FFprobe 版本或所有 Linux / Windows 环境都有同样问题。上游代码保持原样，没有跳过或弱化校验。当前这台 Mac 可采用已验证的 Swift 原生配对路径；其他环境先运行随附测试。

## 本次未做

没有重新安装并渲染 Remotion 模板，没有完成生产内容的画面审查；没有在 Linux / Windows 实机运行，没有执行手机接收、iPhone 识别播放或小红书上传。本次验证的是收录完整性、技能发现和上述本地配对封装，不把这些结果写成设备或平台验收。

## English

The 26 pinned upstream files are byte-identical, licenses and notices are retained, local references and parsers pass, and Skills CLI lists both skills without installing them. The synthetic data validator and the 41 existing Xiaohongshu tests pass. On macOS, the unchanged native Swift path compiled and paired a synthetic 2-second, 30 fps, 320×240 silent H.264/JPEG sample at 1 second; metadata readback, PHLivePhoto loading and .pvt packaging passed without Photos import.

The portable Python suite did not fully pass with Python 3.12.14, Pillow 11.3.0, imageio-ffmpeg 0.6.0's FFmpeg 7.1 and Remotion 4.0.530's ffprobe n7.1: two of four test methods passed; the other two produced three error records because metadata packet `duration_time` was absent. Upstream runtime code is unchanged, and no validation was bypassed. This result applies to this tested combination; it does not establish failure on every platform or FFprobe version. The native Swift path is verified on this Mac. Remotion rendering, Linux/Windows execution, iPhone import/playback and social-platform upload were not rerun.
