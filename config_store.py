#!/usr/bin/env python3
"""Хранение настроек аккаунтов: текст ответа и вкл/выкл в data/autoreply_config.json."""
import json
import logging
from pathlib import Path

import config

log = logging.getLogger("configstore")


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {"accounts": {}}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)

    @property
    def accounts(self) -> dict:
        return self.data["accounts"]

    def acc(self, slot: int) -> dict:
        entry = self.accounts.setdefault(str(slot), {})
        entry.setdefault("reply_text", config.DEFAULT_REPLY)
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

    def drop_missing(self, active_slots: list[int]) -> None:
        removed = [key for key in self.accounts if int(key) not in active_slots]
        for key in removed:
            self.accounts.pop(key, None)
        if removed:
            self.save()