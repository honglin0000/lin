# LiveCanvas

[简体中文](README.md) | English

Create designed covers, animations and Apple Live Photo resources from a topic, text or supplied materials. This directory vendors [pengchujin/livecanvas](https://github.com/pengchujin/livecanvas), retaining the original authorship and licenses. See [upstream provenance](UPSTREAM.md) for the pinned revision and import scope.

## Ask an AI assistant to install

Send this to an assistant that can access the network, execute code and persist skills:

> Install the LiveCanvas skill from https://github.com/honglin0000/lin-tools. First read skills/livecanvas/README.en.md, install the entire skills/livecanvas directory as a skill without replacing my other skills, then read its SKILL.md and check the required environment. Report installation and environment status first; wait for my topic before producing images.

Environments with Skills CLI can also run:

```bash
npx skills add honglin0000/lin-tools --skill livecanvas -g
```

For manual installation, copy this entire directory into your assistant's skill directory, retaining every subdirectory. The skill name is `livecanvas`; [SKILL.md](SKILL.md) is its entry point and is written in Chinese. Skill installation does not install rendering dependencies or prove that a Live Photo has been produced.

## Example request after installation

> Use LiveCanvas to turn this material into a set of Xiaohongshu Live images. Decide the image count, each image's role and the cover from the content first. Keep text readable and make the main subject visibly change. Add no background music. Deliver a playable preview and numbered .pvt resource packages.

You can supply photos, screenshots, comparison materials or data. Choose image count, colors and composition to suit the material. The bundled line chart and data are synthetic toolchain examples; replace them with verified content for real work.

## Environment and workflow

- Rendering: Node.js / npm, Python 3, FFmpeg / ffprobe and the required fonts. Install Remotion dependencies in a separate project directory.
- Live Photo pairing: the portable path requires Python 3.10+, Pillow 10–11 and FFmpeg / ffprobe. macOS can alternatively use the native Swift path with Xcode Command Line Tools.
- Detailed guides, in Chinese: [production](references/production.md), [portable pairing](references/portable-live-photo.md) and [.pvt packaging](references/direct-delivery.md).

Keep covers, video, paired resources, .pvt and validation records in the project. A .pvt contains the paired photo, video and metadata; the receiving application must support Live Photos. File generation, local loading, phone recognition and platform playback require separate evidence. No automatic Photos import or publishing.

## Local checks

Native macOS pairing, local loading and packaging passed in this import check. The portable Python tests encountered a missing FFprobe field in the tested combination. See [import validation](VALIDATION.md) for evidence and limits.

Prepare the Python dependencies above, then run from this directory:

```bash
python3 scripts/validate_data.py assets/remotion/data.json --allow-demo
python3 scripts/test_portable_live_photo.py
```

The first command validates the synthetic sample structure. The second tests pairing, packaging, input protection and corruption detection. For rendering checks, copy the template to a separate project and follow the production guide. Keep generated artifacts outside this skill directory.

## Licenses

LiveCanvas is [MIT](LICENSE). The portable metadata component retains its [Apache-2.0 license](scripts/portable_live_photo/LICENSE) and [NOTICE](scripts/portable_live_photo/NOTICE). See [third-party notices](THIRD_PARTY_NOTICES.md).
