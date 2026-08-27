#!/usr/bin/env python3
"""TG Автоответчик с неограниченным числом рабочих аккаунтов.

Аккаунт подключается просто загрузкой файла accN.session в папку data/
(или строкой ACC{n}_SESSION). У каждого аккаунта свой текст автоответа,
управление — через админ-бота в Telegram.

Для Bothost: задай переменные окружения
  BOT_TOKEN, ADMIN_ID, API_ID, API_HASH
  (BOT_TOKEN задаётся автоматически при создании бота на bothost).
"""
import asyncio
import logging
import sys
import time

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

import config
from accounts import SessionStore
from config_store import ConfigStore
from engine import AutoReplyEngine
from handlers import Handlers, setup_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("main")


class App:
    def __init__(self):
        self.started = time.time()
        self.cfg = ConfigStore(config.CONFIG_PATH)
        self.store = SessionStore(config)
        self.engine = AutoReplyEngine(self.store, self.cfg)


def check_settings() -> list[str]:
    problems = []
    if not config.API_ID or not config.API_HASH:
        problems.append("API_ID/API_HASH не заданы (my.telegram.org)")
    if not config.BOT_TOKEN:
        problems.append("BOT_TOKEN не задан (@BotFather)")
    if not config.ADMIN_ID:
        problems.append("ADMIN_ID не задан (твой Telegram ID)")
    return problems


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Открыть панель управления"),
        ]
    )


async def main() -> None:
    problems = check_settings()
    if problems:
        raise SystemExit("Ошибка настроек: " + "; ".join(problems))

    app = App()
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)

    dp = Dispatcher()
    setup_handlers(dp, Handlers(app))

    polling = asyncio.create_task(dp.start_polling(bot))
    log.info("Подключаю рабочие аккаунты...")
    await app.engine.reload()

    try:
        await app.engine.idle()
    finally:
        polling.cancel()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Бот остановлен.")
    except SystemExit as exc:
        if exc.code:
            print(exc.code, file=sys.stderr)
        log.info("Бот остановлен.")