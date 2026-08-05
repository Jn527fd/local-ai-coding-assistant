# Support and Hotfix Guidance

This project is intended for local or trusted-network deployments. Support
requests and hotfixes should protect user data first.

## Before Opening an Issue

Collect only metadata needed to reproduce the problem:

- App version, branch, or commit SHA.
- Operating system and install mode: local Python/Node, development Compose, or
  production Compose template.
- The exact command or workflow that failed.
- Relevant test or command output after removing private paths and secrets.
- Whether Ollama is installed, running, and reachable, if the issue involves AI
  execution.
- Whether the issue reproduces with fake/default tests, live Ollama smoke
  tests, or both.

Do not share API keys, session cookies, CSRF values, passwords, prompts, chat
messages, uploaded documents, OCR text, generated vector indexes, private source
code, or full local file paths in public issues.

## Diagnostics Bundle

The diagnostics support-bundle endpoint exports redacted metadata only by
default. Still review the exported `local-ai-support-bundle.json` before
sharing it.

Useful areas to include in an issue:

- Runtime health summary.
- Model/provider availability.
- Document/index/job status.
- Vector backend health.
- Recent redacted warnings or errors.

## Triage Levels

- Critical: suspected secret leak, data loss, auth bypass, unsafe public
  exposure, or repeatable failure to start after documented install steps.
- High: repeatable crash, migration failure, backup/restore failure, broken
  login, broken chat, or broken document indexing in default configuration.
- Medium: degraded retrieval quality, optional adapter/tool failure, confusing
  diagnostics, or non-blocking UI regression.
- Low: copy polish, docs clarification, or optional workflow improvement.

## Hotfix Workflow

Use a small branch from the release tag when one exists. If the stable tag has
not been created yet, branch from the release candidate branch or `main`.

```bash
git switch main
git pull
git switch -c hotfix/short-description
```

Hotfix rules:

- Keep the change focused on the defect.
- Add or update regression tests.
- Update `CHANGELOG.md` and relevant public docs.
- Run the smallest targeted tests first, then the full relevant suite.
- Do not add feature work in a hotfix branch.
- Back up local `data/` before applying deployment hotfixes.

After verification, merge through the normal review path and retag only if the
project has an approved release/tag workflow for the target version.
