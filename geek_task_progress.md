# GeekezBrowser Migration Progress
Date: 2026-01-22

## Goals
- Replace BitBrowser control with GeekezBrowser
- Add a new Geek GUI entry (keep Bit flow intact)
- Hide create-parameter panel
- Use accounts.txt as environment list

## Tasks
- [completed] Validate Geek API and implement geek_browser_api.py
- [completed] Implement geek_process.py (account loading, create/launch/close, SheerLink/bind/auto orchestration)
- [completed] Create geek_gui.py (new GUI entry, no create parameters)
- [completed] Run lsp_diagnostics on new/changed files
- [completed] Smoke run the script

## Completed
- Reviewed Geek template scripts and original GUI workflow
- Implemented `2dev/geek/geek_browser_api.py` (health + profile file helpers + launch/close wrapper)
- Implemented `2dev/geek/geek_process.py` (accounts.txt envs + SheerLink/auto flow)
- Implemented `2dev/geek/geek_gui.py` (Geek GUI: accounts.txt list, no create-parameter panel)
- Added Geek GUI entry button to `create_window_gui.py` (keep Bit flow intact)
- Added `verify_single()` to `sheerid_verifier.py` (auto flow expected this API)

## Notes
- Local environment: `GET http://127.0.0.1:19527/health` returns ok (version 3.3.45), but `POST /profiles/{id}/launch` and other probed endpoints returned 404. Need to validate on the target GeekezBrowser build (endpoint/port may differ).
- `lsp_diagnostics` tool is unavailable here (basedpyright missing). Used `python3 -m py_compile` as a syntax check for new/changed files.
- Current env missing `PyQt6`, so GUI cannot be launched here (code compiles).
- `2dev/geek/geek_process.py` no longer depends on `create_window.py` (avoids requiring `selenium` just to parse accounts/proxies).
