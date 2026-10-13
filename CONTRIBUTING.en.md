# Contributing to Xiaohongshu Topic Scout

[简体中文](CONTRIBUTING.md) | English

Users and developers are welcome to contribute. You do not need to write code to share ideas, describe your experience, or point out unclear instructions.

## Suggest an Improvement or Report a Problem

Check the [existing issues](https://github.com/honglin0000/lin/issues) first. If you cannot find a matching discussion, [open a new issue](https://github.com/honglin0000/lin/issues/new/choose) and briefly explain:

- The problem you want to solve, or the step where you got stuck.
- What you expected to happen and what actually happened.
- If useful, error messages or screenshots with account credentials removed.

Use everyday language in **English or Chinese**; technical terms are not required. Do not upload passwords, cookies, keys, or logs containing credentials.

## Submit a Change

1. Click **Fork** at the top right of the repository to create your own copy.
2. Create a branch in your copy and edit the code or documentation.
3. Click **Contribute → Open pull request** to propose your changes to the `main` branch of `honglin0000/lin`. You can also view the repository's [pull requests](https://github.com/honglin0000/lin/pulls).
4. Explain the problem, the resulting behavior, and the checks you performed. The maintainer will review the proposal and decide whether to merge it; opening a PR does not directly change this repository.

For code changes, run:

```bash
python3 -m unittest discover -s tests -v
```

For small documentation changes, checking the text and links is enough. State which checks you have not performed, and record mock API tests separately from real Xiaohongshu searches.

## Help Most Needed

- Reproducible feedback on Grok Bot import and real deployment.
- Search API changes and problems with date or engagement data handling.
- Improvements to the quality of topic candidates and original content ideas.
- Clearer usage documentation in English and Chinese.

The project currently only searches, reads, and analyzes. Preserve source links, unknown-data markers, and demo-data labels. Do not describe a search sample as a platform-wide trending list.
