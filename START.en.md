# One-Message Automatic Setup

[简体中文](START.md) | English

These instructions are for a bot that receives an installation request. Start only when the user explicitly asks to install or configure this project; reading, reviewing, or recommending the repository does not trigger installation. The user only needs to send one request containing the repository link. The bot performs the technical steps below.

## 1. Confirm your capabilities and obtain the complete project

Check the network access, file access, command execution, and persistent role/skill management capabilities actually available in your current environment. Do not guess Grok Bot tool names, APIs, or skill paths. Confirm Python 3.9+, obtain all files in this repository, record the version, and read [PROFILE.en.md](PROFILE.en.md) and [the English skill instructions](skills/xhs-topic-scout/SKILL.en.md). If a local copy already exists, check for local changes first; do not force an overwrite or reset.

If command execution or persistent storage is unavailable, explain which capability the current environment lacks and that setup is not complete. A tutorial response does not count as installation. Do not ask the user to run commands you can run yourself.

## 2. Save the role and the complete skill

- By default, add this project's research capability to the current bot while preserving its existing name, responsibilities, and other skills. Persist the research responsibilities from `PROFILE.en.md` as a "Xiaohongshu topic research" module. A blank, dedicated bot may adopt the complete profile. Create a new bot only if the user explicitly requests one; repeated installation must not create duplicates.
- Use the skill storage/registration capabilities actually supported by the current product to install the entire `skills/xhs-topic-scout/` directory in a skill library discoverable by the current bot. Preserve the relative locations of `scripts/scout.py` and `scripts/setup.py`. The canonical skill entry point remains `SKILL.md`; `SKILL.en.md` is an English translation of the same skill, not a second skill to register. If a skill with the same name already exists, compare its contents first. Back up and merge any local changes; do not delete other skills.
- Read back the persisted role and the registered skill. Confirm that natural-language requests to research recent Xiaohongshu topics, trends, or content ideas will use this skill. Writing instructions to an ordinary file, saving only the repository link, or promising to remember them in the conversation does not count as completed registration.
- Persist the actual absolute skill path, connection mode (managed by the setup helper / existing service), any custom runtime directory or service URL, and a reference to the secure credential configuration. Do not write plaintext credentials into the role, reports, or conversation. Replace `<skill-directory>` below with the actual path. The Python scripts manage only the data service; they cannot prove that the bot's role or skill has been registered.

## 3. Automatically establish a connection in the same environment

First determine the connection mode. If the current bot already has a configuration, use its secure environment configuration to run `scout.py check`. Reuse the service if the interface works; do not reinstall solely because its version differs. An existing service that is not logged in can be retained and connected through the upstream login flow. Use the setup helper only when no configured, usable service is available:

```text
python3 <skill-directory>/scripts/setup.py ensure
```

On supported platforms, the setup helper downloads and verifies a pinned upstream version, generates a private connection configuration, starts the service only on `127.0.0.1:18060`, and then checks login status. The default runtime directory is `~/.local/share/xhs-topic-scout`. If only a specific directory persists in the cloud environment, first set `XHS_SCOUT_HOME` to this bot's private persistent directory, record that path in the bot's connection instructions, and reuse it for every subsequent invocation.

For an existing, independently configured service, reuse verified working `XHS_MCP_URL` / `XHS_MCP_TOKEN` settings and call `scout.py` directly. Do not take over an occupied port, kill other processes, or move existing cookies. A statement about the service from a previous conversation is not evidence of a current connection. The setup helper and an existing manual deployment are two distinct connection modes; do not mix their private configurations.

The first browser download may take some time. Report progress only from actual execution results. If system libraries are missing, the platform is unsupported, or a network request fails, explain the specific stage and error. Do not disable security checks, automatically elevate privileges, expose public ports, or create tunnels. Do not retry the same error indefinitely.

## 4. Ask the user to scan a QR code when login is required

When the result is `needs_login`, run:

```text
python3 <skill-directory>/scripts/setup.py login
```

Display the image at the returned `qr_path` using the current conversation's private image display capability, and ask the user to scan it with the Xiaohongshu app. Do not upload the login QR code publicly or request a password or cookies. The QR code is valid for approximately four minutes. Do not repeatedly generate new codes while waiting; refresh it after it expires.

After the user finishes, run `setup.py status`. Continue to a real search only when `logged_in: true`. If a CAPTCHA or platform access restriction appears, have the user handle it through the official interface; do not bypass it. For an existing manually deployed service, use the upstream login interface to complete the equivalent flow.

## 5. Verify that one message triggers actual work

Run the repository tests first, then perform a real search using the user's existing keywords. If the installation request contains no keywords, use "AI办公" and "会议纪要" as explicitly labeled functional verification examples. There is no need to ask the user for keywords just for this check:

```text
python3 -B -m unittest discover -s <repository-directory>/tests -v
python3 <skill-directory>/scripts/setup.py run search --keywords "AI办公" "会议纪要" --days 7 --top 10 --detail-limit 30 --output-dir <private-report-directory-for-this-run>
```

Use structured arguments or correct shell escaping; do not concatenate user input directly into a command. When calling an existing manual service, use `scout.py search` with the equivalent arguments.

Read the actual JSON from this run: `demo` must be `false`. Check `partial`, `summary`, `errors`, and the `notes` whose publication dates have been verified, then summarize topics and original content ideas according to the skill instructions. If there are no valid notes, explain why. Do not present `sample` data, web search summaries, or fabricated notes as a successful Xiaohongshu search.

After installation, use a new conversation or independent session supported by the current product. Provide only a natural-language request such as "Help me research Xiaohongshu topics about AI office work from the past week." Verify that the bot discovers the skill and reuses the existing connection without being given paths or commands again. If the product does not support this verification method, mark it as unverified; do not claim the capability works across sessions. Subsequently, use the saved skill and connection automatically. Ask for user involvement only when login expires, permissions require it, or an unrecoverable error occurs. Do not require reinstallation or technical parameters for every request.

## 6. Report completion accurately

Check and briefly report each item separately:

1. The role was persisted and successfully read back.
2. The complete skill is registered and discoverable.
3. The data service is actually reachable.
4. The Xiaohongshu login is actually valid.
5. Whether this real search and its source report succeeded, and whether the results are partial.

Keep verification records with credentials removed and links to private reports. The first two items require evidence from the product's native save/read capabilities; passing Python tests does not prove they succeeded. Explicitly mark any missing step as incomplete.

Handle only this project's research connection and capabilities. An installation request does not authorize publishing notes, commenting, liking, saving posts, following accounts, sending external messages, sharing account credentials, or scheduling automated tasks.
