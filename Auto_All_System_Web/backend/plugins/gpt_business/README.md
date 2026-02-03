# GPT Business Plugin

This plugin exposes a "GPT专区" workflow in Auto_All_System_Web.

Key points:

- All configuration is managed via Web UI (PluginState.settings). Users do NOT edit config.toml/team.json.
- Automation logic is implemented inside this project (no external repo mount/subprocess).
- Job artifacts are stored under `MEDIA_ROOT/gpt_business/jobs/<task_id>/` and are downloadable via plugin endpoints.
- Trace logs are stored under `logs/trace/trace_<celery_task_id>_<email>.log` (json line + human line).

## Trace

- Trace endpoint: `GET /api/v1/plugins/gpt-business/celery-tasks/{task_id}/trace/?email=<email>`
- Trace file naming: `trace_<celery_task_id>_<email>.log` (falls back to `trace_<celery_task_id>.log`)

## Trace Cleanup

- Management command (dry-run by default): `python manage.py cleanup_trace`
- Apply deletion: `python manage.py cleanup_trace --apply`
- API endpoint:
  - GET `/api/v1/plugins/gpt-business/settings/trace-cleanup/` (dry-run)
  - POST `/api/v1/plugins/gpt-business/settings/trace-cleanup/` with `{"apply": true}`
- Celery beat schedule: runs daily 03:30 (env `GPT_TRACE_CLEANUP_ENABLED`, default true)
- Config: `PluginState.settings.trace_cleanup`

## Flows

- invite_only: only create emails (GPTMail) + invite to OpenAI Team

## Docs

- Overview: `docs/AUTOMATION_FLOW.md`
- Maintenance guide (self_register / auto_invite / sub2api_sink): `docs/AUTO_INVITE_MAINTENANCE.md`

## Requirements

- drissionpage (browser automation)

Note: DrissionPage requires a working Chromium/Chrome environment on the server.
