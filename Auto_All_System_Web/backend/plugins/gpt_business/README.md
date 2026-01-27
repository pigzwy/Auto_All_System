# GPT Business Plugin

This plugin exposes a "GPT专区" workflow in Auto_All_System_Web.

Key points:

- All configuration is managed via Web UI (PluginState.settings). Users do NOT edit config.toml/team.json.
- For compatibility with the legacy implementation, the backend will generate per-job `config.toml` and `team.json` internally and execute the legacy runner.
- Job artifacts are stored under `MEDIA_ROOT/gpt_business/jobs/<task_id>/` and are downloadable via plugin endpoints.

## Flows

- invite_only: only create emails (GPTMail) + invite to OpenAI Team
- legacy_run: direct run `oai-team-auto-provisioner/run.py` (DrissionPage based), keeps original behavior

## Requirements

The legacy flow depends on these Python packages (pinned in `backend/requirements/base.txt`):

- drissionpage
- tomli
- rich

Note: DrissionPage requires a working Chromium/Chrome environment on the server.

## Legacy Repo Path

Default legacy repo path:

- `/home/pig/github/oai-team-auto-provisioner`

You can override by setting `legacy_repo_path` in plugin settings (admin only).
