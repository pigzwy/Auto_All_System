# GPT Business Plugin

This plugin exposes a "GPT专区" workflow in Auto_All_System_Web.

Key points:

- All configuration is managed via Web UI (PluginState.settings). Users do NOT edit config.toml/team.json.
- Automation logic is implemented inside this project (no external repo mount/subprocess).
- Job artifacts are stored under `MEDIA_ROOT/gpt_business/jobs/<task_id>/` and are downloadable via plugin endpoints.

## Flows

- invite_only: only create emails (GPTMail) + invite to OpenAI Team

## Docs

- Overview: `docs/AUTOMATION_FLOW.md`
- Maintenance guide (self_register / auto_invite / sub2api_sink): `docs/AUTO_INVITE_MAINTENANCE.md`

## Requirements

- drissionpage (browser automation)

Note: DrissionPage requires a working Chromium/Chrome environment on the server.
