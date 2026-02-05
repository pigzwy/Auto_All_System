from __future__ import annotations

import copy
from typing import Any, Callable

from django.db import transaction
from django.utils import timezone

from apps.plugins.models import PluginState


PLUGIN_NAME = "gpt_business"


def get_plugin_state() -> PluginState:
    # 默认标记为 installed/enabled，方便首次接入时不必手工创建 PluginState。
    # 若你的环境有严格的插件启用流程，可以通过 init_plugins.py 统一管理。
    state, _ = PluginState.objects.get_or_create(
        name=PLUGIN_NAME,
        defaults={
            "installed": True,
            "enabled": True,
            "enabled_at": timezone.now(),
            "installed_at": timezone.now(),
            "settings": {},
        },
    )
    return state


def get_settings() -> dict[str, Any]:
    state = get_plugin_state()
    return state.settings or {}


def update_settings(mutator: Callable[[dict[str, Any]], dict[str, Any] | None]) -> dict[str, Any]:
    with transaction.atomic():
        state, _ = PluginState.objects.select_for_update().get_or_create(
            name=PLUGIN_NAME,
            defaults={
                "installed": True,
                "enabled": True,
                "enabled_at": timezone.now(),
                "installed_at": timezone.now(),
                "settings": {},
            },
        )

        settings: dict[str, Any] = copy.deepcopy(state.settings or {})
        new_settings = mutator(settings)
        if new_settings is not None:
            settings = new_settings

        state.settings = settings
        state.save(update_fields=["settings", "updated_at"])
        return settings


def list_tasks(settings: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = settings.get("tasks") or []
    if isinstance(tasks, list):
        return tasks
    return []


def find_task(settings: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    for task in list_tasks(settings):
        if str(task.get("id")) == str(task_id):
            return task
    return None


def patch_task(task_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    def mutator(settings: dict[str, Any]) -> dict[str, Any]:
        tasks = list_tasks(settings)
        updated: dict[str, Any] | None = None

        for i, task in enumerate(tasks):
            if str(task.get("id")) != str(task_id):
                continue

            new_task = {**task, **patch}
            tasks[i] = new_task
            updated = new_task
            break

        settings["tasks"] = tasks
        settings["last_updated"] = timezone.now().isoformat()
        return settings

    updated_settings = update_settings(mutator)
    return find_task(updated_settings, task_id)


def add_task(record: dict[str, Any]) -> dict[str, Any] | None:
    def mutator(settings: dict[str, Any]) -> dict[str, Any]:
        tasks = list_tasks(settings)
        tasks.insert(0, record)
        settings["tasks"] = tasks
        settings["last_updated"] = timezone.now().isoformat()
        return settings

    updated_settings = update_settings(mutator)
    return find_task(updated_settings, str(record.get("id")))


def clear_tasks() -> int:
    def mutator(settings: dict[str, Any]) -> dict[str, Any]:
        settings["tasks"] = []
        settings["last_updated"] = timezone.now().isoformat()
        return settings

    current = len(list_tasks(get_settings()))
    update_settings(mutator)
    return current


def clear_tasks_for_mother(mother_id: str, *, keep_in_progress: bool = True) -> int:
    mother_id = str(mother_id or "").strip()
    if not mother_id:
        return 0

    in_progress_statuses = {"queued", "pending", "running"}
    removed = 0

    def mutator(settings: dict[str, Any]) -> dict[str, Any]:
        nonlocal removed
        tasks = list_tasks(settings)
        kept: list[dict[str, Any]] = []

        for t in tasks:
            if str(t.get("mother_id") or "") != mother_id:
                kept.append(t)
                continue

            status = str(t.get("status") or "").strip().lower()
            if keep_in_progress and status in in_progress_statuses:
                kept.append(t)
                continue

            removed += 1

        settings["tasks"] = kept
        settings["last_updated"] = timezone.now().isoformat()
        return settings

    update_settings(mutator)
    return removed


def list_accounts(settings: dict[str, Any]) -> list[dict[str, Any]]:
    accounts = settings.get("accounts") or []
    if isinstance(accounts, list):
        return accounts
    return []


def find_account(settings: dict[str, Any], account_id: str) -> dict[str, Any] | None:
    for acc in list_accounts(settings):
        if str(acc.get("id")) == str(account_id):
            return acc
    return None


def add_account(record: dict[str, Any]) -> dict[str, Any] | None:
    def mutator(settings: dict[str, Any]) -> dict[str, Any]:
        accounts = list_accounts(settings)
        accounts.insert(0, record)
        settings["accounts"] = accounts
        settings["last_updated"] = timezone.now().isoformat()
        return settings

    updated_settings = update_settings(mutator)
    return find_account(updated_settings, str(record.get("id")))


def patch_account(account_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    def mutator(settings: dict[str, Any]) -> dict[str, Any]:
        accounts = list_accounts(settings)
        updated: dict[str, Any] | None = None

        for i, acc in enumerate(accounts):
            if str(acc.get("id")) != str(account_id):
                continue
            new_acc = {**acc, **patch}
            accounts[i] = new_acc
            updated = new_acc
            break

        settings["accounts"] = accounts
        settings["last_updated"] = timezone.now().isoformat()
        return settings

    updated_settings = update_settings(mutator)
    return find_account(updated_settings, account_id)


def delete_account(account_id: str) -> bool:
    def mutator(settings: dict[str, Any]) -> dict[str, Any]:
        accounts = list_accounts(settings)
        accounts = [a for a in accounts if str(a.get("id")) != str(account_id) and str(a.get("parent_id")) != str(account_id)]
        settings["accounts"] = accounts
        settings["last_updated"] = timezone.now().isoformat()
        return settings

    before = len(list_accounts(get_settings()))
    after_settings = update_settings(mutator)
    after = len(list_accounts(after_settings))
    return after < before
