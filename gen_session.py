#!/usr/bin/env python3
"""Генерация сессии для рабочего аккаунта (запускать ЛОКАЛЬНО на своём ПК).

Режим 1 → создаёт файл accN.session, который загружается в папку data/ на хостинге.
Режим 2 → печатает строку-сессию для переменной ACC{N}_SESSION в панели хостинга.

Требуется:  pip install telethon
"""
import asyncio
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MAX_ACCOUNTS = 50


async def go() -> None:
    raw_id = input("API_ID (число, с my.telegram.org): ").strip()
    if not raw_id.isdigit():
        raise SystemExit("API_ID должен быть числом (my.telegram.org/apps)")
    api_id = int(raw_id)
    api_hash = input("API_HASH (с my.telegram.org): ").strip()
    if not api_hash:
        raise SystemExit("API_HASH пустой")

    slot_raw = input(f"Номер слота (1-{MAX_ACCOUNTS}, Enter = 1): ").strip() or "1"
    if not slot_raw.isdigit() or not 1 <= int(slot_raw) <= MAX_ACCOUNTS:
        raise SystemExit("Неверный номер слота")
    slot = int(slot_raw)

    mode = input("Режим: [1] файл accN.session  [2] строка-сессия: ").strip() or "1"
    if mode == "2":
        client = TelegramClient(StringSession(), api_id, api_hash)
    else:
        path = f"acc{slot}.session"
        client = TelegramClient(path, api_id, api_hash)

    await client.start()
    me = await client.get_me()
    who = f"@{me.username}" if me.username else (me.first_name or f"id {me.id}")

    if mode == "2":
        print("\n" + "=" * 56)
        print("Строка-сессия (сначала, ACC%d_SESSION в панели Bothost):" % slot)
        print("=" * 56)
        print(client.session.save())
        print("=" * 56)
    else:
        print(f"\nГотово! Файл acc{slot}.session создан.")
        print("Закинь его в папку data/ на хостинге и нажми «🔄 Сканировать».")
    print(f"Аккаунт: {who} (слот {slot})")

    await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(go())
    except KeyboardInterrupt:
        print("\nПрервано.")
        sys.exit(1)