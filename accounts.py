#!/usr/bin/env python3
"""Обнаружение рабочих аккаунтов: файлы accN.session + строковые сессии из env."""
import json
import logging
import os
import re
from pathlib import Path

log = logging.getLogger("accounts")

_FILE_NUM = re.compile(r"(?:acc)?(\d+)$")
KIND_FILE = "файл"
KIND_STRING = "строка"


def _load_json(path: Path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


class SessionStore:
    """Собирает источники сессий из файлов *.session и env ACC{n}_SESSION.

    Файл `acc5.session` или `5.session` → слот 5.
    Файл с произвольным именем получает стабильный слот из data/assigned.json.
    Строки из env имеют приоритет над файлом в том же слоте.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self._assigned = _load_json(cfg.ASSIGNED_PATH, {})
        self.items: dict[int, tuple[str, str]] = {}

    def _next_free(self, used: set[int]) -> int:
        n = 1
        while n in used:
            n += 1
        return n

    def _collect_files(self) -> tuple[list[tuple[int, Path]], list[tuple[str, Path]]]:
        numbered: list[tuple[int, Path]] = []
        others: list[tuple[str, Path]] = []
        seen = set()
        for folder in (self.cfg.DATA_DIR, self.cfg.BASE_DIR):
            try:
                candidates = sorted(folder.glob("*.session"))
            except Exception as exc:
                log.warning("не могу сканировать %s: %s", folder, exc)
                continue
            for path in candidates:
                resolved = str(path.resolve())
                if resolved in seen:
                    continue
                seen.add(resolved)
                match = _FILE_NUM.fullmatch(path.stem)
                if match:
                    numbered.append((int(match.group(1)), path))
                else:
                    others.append((path.stem, path))
        return numbered, others

    def scan(self) -> dict[int, tuple[str, str]]:
        items: dict[int, tuple[str, str]] = {}
        used: set[int] = set()

        numbered, others = self._collect_files()
        for slot, path in numbered:
            if 1 <= slot <= self.cfg.MAX_ACCOUNTS and slot not in used:
                items[slot] = (str(path), KIND_FILE)
                used.add(slot)

        for name, path in others:
            slot = self._assigned.get(name)
            if slot is not None and (slot in used or not 1 <= slot <= self.cfg.MAX_ACCOUNTS):
                slot = None
            if slot is None:
                slot = self._next_free(used)
                self._assigned[name] = slot
                _save_json(self.cfg.ASSIGNED_PATH, self._assigned)
            if 1 <= slot <= self.cfg.MAX_ACCOUNTS:
                items[slot] = (str(path), KIND_FILE)
                used.add(slot)

        for n in range(1, self.cfg.MAX_ACCOUNTS + 1):
            value = os.getenv(f"ACC{n}_SESSION", "").strip()
            if value:
                items[n] = (value, KIND_STRING)
                used.add(n)

        legacy = os.getenv("SESSION_STRING", "").strip()
        if legacy and 1 not in items:
            items[1] = (legacy, KIND_STRING)

        self.items = items
        return items