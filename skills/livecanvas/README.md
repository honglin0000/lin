# LiveCanvas · 实况画布

简体中文 | [English](README.en.md)

把主题、文字或已有素材做成有封面、有动效的 Live 图片，适合知识讲解、产品对比和信息图。

## 让 AI 助手安装

把下面这段发给能联网、执行代码并保存技能的 AI 助手：

> 请给自己安装 https://github.com/honglin0000/lin-tools 中的 LiveCanvas 实况图片技能。先读 skills/livecanvas/README.md，把 skills/livecanvas 整个目录安装为技能，保留已有技能，再读取其中的 SKILL.md 并检查所需环境。先告诉我安装和环境检查结果；等我提供主题后再制作。

支持 Skills CLI 的环境也可运行：

```bash
npx skills add honglin0000/lin-tools --skill livecanvas -g
```

手动安装时，把本目录整体复制到所用助手的技能目录，保留所有子目录；技能名称为 `livecanvas`，入口是 [SKILL.md](SKILL.md)。安装技能不会自动安装渲染依赖，也不代表已经完成实况图片制作。

## 装好后这样说

> 用 LiveCanvas 把这段内容做成一套小红书 Live 图片。先按内容确定图数、各图分工与封面，再制作动效；文字保持清晰，主体有可见变化，不加背景音乐。请给我可播放预览和按图序编号的 .pvt 实况包。

也可以提供产品照片、截图、对比材料或数据。先按材料设计画面，图片数量、配色和布局随内容确定。自带折线图及数据是工具链示例，正式作品须替换为已核实内容。

## 环境与使用

- 画面和动效：Node.js / npm、Python 3、FFmpeg / ffprobe，以及内容所需字体；Remotion 依赖安装在本次独立工程里。
- Live 配对：跨平台路径需要 Python 3.10+、Pillow 10–11、FFmpeg / ffprobe。macOS 也可选择 Swift 原生配对，需要 Xcode Command Line Tools。
- 使用步骤：[运行与交付](references/production.md)、[跨平台 Live Photo](references/portable-live-photo.md)、[实况包封装](references/direct-delivery.md)。

完整工程保留封面、视频、配对资源、.pvt 和验证记录。`.pvt` 内含配对照片、视频和元数据，接收端须支持 Live Photo；文件生成、本机加载、手机识别和平台播放分别核验，不把其中一步视作全部完成。不自动导入相册或发布。

## 本地检查

本次 macOS 原生配对、本机加载和打包已通过；便携 Python 测试在当前 FFprobe 组合中有字段读取错误。实际范围与限制见 [收录验证](VALIDATION.md)。

Python 路径先准备上述依赖，在本目录运行：

```bash
python3 scripts/validate_data.py assets/remotion/data.json --allow-demo
python3 scripts/test_portable_live_photo.py
```

第一条只校验合成示例的结构；第二条测试配对、封装、输入保护和损坏检测。渲染验证按运行指南复制模板到独立工程后执行。测试生成物留在本地，不放回技能目录。

## 许可

LiveCanvas 主体为 [MIT](LICENSE)；便携元数据组件保留自己的 [Apache-2.0 许可证](scripts/portable_live_photo/LICENSE)和 [NOTICE](scripts/portable_live_photo/NOTICE)。详见 [第三方声明](THIRD_PARTY_NOTICES.md)。
