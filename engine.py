#!/usr/bin/env python3
"""Движок автоответчика: подключение юзерботов и обработка входящих сообщений."""
import asyncio
import logging
import time
from pathlib import Path

from telethon import TelegramClient, events
from telethon.sessions import StringSession

import config
from accounts import KIND_FILE
from config_store import ConfigStore

log = logging.getLogger("engine")


class AutoReplyEngine:
    def __init__(self, store, cfg: ConfigStore):
        self.store = store
        self.cfg = cfg
        self.clients: dict[int, TelegramClient] = {}
        self.names: dict[int, str] = {}
        self.errors: dict[int, str] = {}
        self._file_mtimes: dict[int, float | None] = {}
        self._last = {}

    def name(self, slot: int) -> str:
        return self.names.get(slot, f"аккаунт {slot}")

    @classmethod
    def _make_client(cls, value: str, kind: str) -> TelegramClient:
        session = StringSession(value) if kind == "строка" else value
        return TelegramClient(
            session,
            config.API_ID,
            config.API_HASH,
            connection_retries=8,
            retry_delay=2,
            flood_sleep_threshold=60,
        )

    async def start_slot(self, slot: int) -> bool:
        if slot in self.clients:
            return True
        entry = self.store.items.get(slot)
        if not entry:
            return False
        value, kind = entry
        try:
            client = self._make_client(value, kind)
        except Exception as exc:
            self.errors[slot] = f"неверная строка-сессия: {exc}"
            log.error("Аккаунт %s: невалидная строка-сессия — %s", slot, exc)
            return False
        self._plug(client, slot)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise RuntimeError("сессия не авторизована (строка/файл повреждены)")
            me = await client.get_me()
            self.clients[slot] = client
            self.names[slot] = (
                f"@{me.username}" if me.username else (me.first_name or f"id {me.id}")
            )
            self.errors.pop(slot, None)
            self._file_mtimes[slot] = self._file_mtime(value) if kind == KIND_FILE else None
            log.info("Аккаунт %s онлайн: %s", slot, self.names[slot])
            return True
        except Exception as exc:
            self.errors[slot] = str(exc)
            log.error("Аккаунт %s не подключился (%s): %s", slot, kind, exc)
            await self._safe_disconnect(client)
            return False

    @staticmethod
    async def _safe_disconnect(client: TelegramClient) -> None:
        try:
            if client.is_connected():
                await client.disconnect()
        except Exception:
            pass

    @staticmethod
    def _file_mtime(value: str):
        try:
            return Path(value).stat().st_mtime
        except Exception:
            return None

    async def stop_slot(self, slot: int) -> None:
        client = self.clients.pop(slot, None)
        self.names.pop(slot, None)
        self._file_mtimes.pop(slot, None)
        if client is not None:
            await self._safe_disconnect(client)

    async def reload(self) -> dict[int, str]:
        items = self.store.scan()
        for slot in list(self.clients):
            if slot not in items:
                await self.stop_slot(slot)
                continue
            value, kind = items[slot]
            stamp = self._file_mtime(value) if kind == KIND_FILE else None
            if self._file_mtimes.get(slot) != stamp:
                await self.stop_slot(slot)
        started: dict[int, str] = {}
        for slot in sorted(items):
            if slot in self.clients:
                continue
            try:
                ok = await asyncio.wait_for(self.start_slot(slot), timeout=30)
            except asyncio.TimeoutError:
                self.errors[slot] = "таймаут подключения (30 сек)"
                log.error("Аккаунт %s: таймаут подключения", slot)
                ok = False
            if ok:
                started[slot] = self.names.get(slot, "")
        return started

    async def idle(self) -> None:
        # Юзерботы уже запущены через start(); main() ждём вечно,
        # пока Dispatcher не остановлен.
        await asyncio.Event().wait()

    def _plug(self, client: TelegramClient, slot: int) -> None:
        @client.on(events.NewMessage(incoming=True))
        async def handler(event):
            await self._on_incoming(slot, event)

    async def _on_incoming(self, slot: int, event) -> None:
        try:
            if not event.is_private or event.out:
                return
            sender = event.sender_id
            if not sender or sender < 0 or sender in config.SERVICE_IDS:
                return
            acc = self.cfg.acc(slot)
            if not acc.get("enabled", True):
                return
            now = time.time()
            key = (slot, sender)
            if now - self._last.get(key, 0) < self.cfg.cooldown:
                return
            self._last[key] = now
            await event.reply(acc.get("reply_text") or self.cfg.default_reply)
            log.info("[акк %s] ответил %s", slot, sender)
        except Exception as exc:
            log.warning("[акк %s] ошибка автоответа: %s", slot, exc)