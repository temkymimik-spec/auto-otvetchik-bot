#!/usr/bin/env python3
"""Хранение настроек: глобальные (пауза, текст по умолчанию) и по аккаунтам.

Всё лежит в data/autoreply_config.json и правится прямо из бота.
"""
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import config

log = logging.getLogger("configstore")


@dataclass
class Settings:
    cooldown: float
    default_reply: str


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self.data = self._load()
        settings = self.data.setdefault("settings", {})
        settings.setdefault("cooldown", config.COOLDOWN)
        settings.setdefault("default_reply", config.DEFAULT_REPLY)
        self.data.setdefault("accounts", {})

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)

    # ---- глобальные настройки ----
    @property
    def cooldown(self) -> float:
        try:
            return max(0.0, float(self.data["settings"].get("cooldown", config.COOLDOWN)))
        except (TypeError, ValueError):
            return config.COOLDOWN

    @property
    def default_reply(self) -> str:
        return self.data["settings"].get("default_reply") or config.DEFAULT_REPLY

    def set_cooldown(self, value: float) -> None:
        self.data["settings"]["cooldown"] = max(0.0, value)
        self.save()

    def set_default_reply(self, text: str) -> None:
        self.data["settings"]["default_reply"] = text
        self.save()

    # ---- настройки аккаунтов ----
    @property
    def accounts(self) -> dict:
        return self.data["accounts"]

    def acc(self, slot: int) -> dict:
        entry = self.accounts.setdefault(str(slot), {})
        entry.setdefault("reply_text", self.default_reply)
        entry.setdefault("enabled", True)
        return entry

    def set_text(self, slots: list[int], text: str) -> None:
        for slot in slots:
            self.acc(slot)["reply_text"] = text
        self.save()

    def set_enabled(self, slots: list[int], enabled: bool) -> None:
        for slot in slots:
            self.acc(slot)["enabled"] = enabled
        self.save()

    def remove_account(self, slot: int) -> None:
        self.accounts.pop(str(slot), None)
        self.save()