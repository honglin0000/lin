# Validation Record

[简体中文](VALIDATION.md) | English

Date: October 14, 2026 (Beijing time)

The functional checks below are translated from the existing record, not evidence of a new functional test run. Checks for the English documentation are recorded separately at the end.

## Reviewed

- The upstream HTTP API, POST search filter fields, the nested `data` structure in detail responses, millisecond publication timestamps, and engagement counts returned as strings.
- The read-only endpoint allowlist: login status, search, and details.

## Local Automated Validation

- All 41 Python unittest tests passed: 18 collection tests and 23 automated setup tests. These include a local mock HTTP server and end-to-end command-line report export.
- Covered: POST search filters, deduplication across keywords, millisecond timestamps in details, unknown/expired/future dates, zero/negative timestamps, missing engagement counts, exclusion from ranking when metrics are missing, mismatched detail IDs, partial request failures, all searches failing, empty results, and a logged-out state.
- Covered: rejection of non-read-only endpoints and HTTP 302/307 redirects, to prevent forwarding authentication and bypassing the endpoint allowlist.
- Setup helper coverage: downloaded files are not executed when checksum verification fails; repeated installation reuses the existing installation; port conflicts do not cause another service to be taken over; authentication and login status; service startup failures; private file permissions; QR code handling; status checks without side effects; unsupported platforms; and isolation of subprocess credentials and proxy settings. The collection script rejects abbreviated URL arguments to prevent bypassing the address restrictions for managed connections.
- Covered process ID reuse after a service stops: verify the actual executable path, ignore stale state, and restore the service without stopping unrelated processes. A service that is still starting is not started a second time.
- Downloads, processes, and login responses in the automated setup tests use test doubles. All test writes go to temporary directories. These tests were not treated as evidence of a real deployment.
- Demo mode makes no network requests. Its JSON, filenames, and reports distinguish fictional demo data from real collection results.
- The skill-creator `quick_validate.py` check passed, as did Python syntax compilation checks.
- A connection check against the default local service address returned "unable to connect." This was not recorded as a successful real search.
- A real invocation of the new setup helper's `status` command returned `not_running`, `connected=false`, and `logged_in=false`, with exit code 3. It did not create the specified temporary runtime directory.

## Official Release Binary Check

- The new setup helper was used to download the official upstream v2.5.5 binary for macOS arm64. Its SHA256 matched the pinned value. Running `-help` returned exit code 0 and confirmed the `-port`, `-headless`, and `AUTH_TOKEN` configuration interfaces.
- This check did not launch a browser, log in to Xiaohongshu, or perform a search. Downloading and running the Linux release with the new setup helper has not yet been verified in a real Linux environment.

## Not Yet Verified

- Real login and search results using the user's Xiaohongshu account.
- Persistent role instructions, complete skill registration, and invocation across conversations through the new one-sentence installation flow in Grok Bot.
- Real browser startup, QR code scanning, and a complete end-to-end research run with the new setup helper.

Local mock API tests demonstrate how the program handles the expected responses. They do not establish that the Xiaohongshu website will remain accessible or that any user account is connected.

## English Documentation Checks (October 14, 2026)

- Reviewed the English project overview, installation workflow, bot profile, skill instructions, contribution guide, and validation record against the Chinese originals.
- All 33 local document links and the language-switch links passed checks. The English workflow still registers the original complete skill directory, with `SKILL.md` as the registration entry point.
- Re-ran the skill-creator `quick_validate.py` check successfully; the Git diff whitespace check also passed.
- This update changes only documentation and the skill's language entry points. Program tests were not rerun, no data service was installed, and real login and search inside Grok Bot were not tested. The items under "Not Yet Verified" remain outstanding.
