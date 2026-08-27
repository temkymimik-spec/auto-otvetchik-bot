#!/usr/bin/env python3
"""Полностью кнопочная панель управления автоответчиком."""
import logging
import time

from aiogram import Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

import config
import keyboards as kb

log = logging.getLogger("handlers")

ALL = "__all__"
PAGE_SIZE = 10

_PENDING_TEXT: dict[int, str] = {}  # uid -> '__all__' | 'slot:N'
_CTX: dict[int, str] = {}           # uid -> '__all__' | 'slot:N' (для «Ещё»/«Отмена»)


class Handlers:
    def __init__(self, app):
        self.app = app

    # ---------- helpers ----------
    def _admin_msg(self, message: Message) -> bool:
        return bool(message.from_user and message.from_user.id == config.ADMIN_ID)

    def _admin_query(self, query: CallbackQuery) -> bool:
        return bool(query.from_user and query.from_user.id == config.ADMIN_ID)

    @staticmethod
    def _slot_of(query: CallbackQuery) -> int:
        try:
            return int((query.data or "").rsplit(":", 1)[-1])
        except ValueError:
            return 0

    def _slots_known(self) -> list[int]:
        engine = self.app.engine
        return sorted(set(engine.clients) | set(engine.errors) | set(self.app.store.items))

    def _account_card(self, slot: int) -> str:
        acc = self.app.cfg.acc(slot)
        engine = self.app.engine
        state = "🟢 включён" if acc["enabled"] else "🔴 выключен"
        if slot in engine.errors:
            state = f"❌ не в сети ({engine.errors[slot][:50]})"
        return (
            f"👤 <b>{slot}. {engine.name(slot)}</b>\n"
            f"Статус: {state}\n\n"
            f"📝 <b>Текст ответа:</b>\n"
            f"{acc['reply_text']}"
        )

    def _set_text_action(self, target: str, text: str) -> list[int]:
        if target == ALL:
            slots = sorted(self.app.engine.clients)
        else:
            slot = self._target_slot(target)
            slots = [slot] if slot else []
        self.app.cfg.set_text(slots, text)
        return slots

    @staticmethod
    def _target_slot(target: str) -> int | None:
        if target and target.startswith("slot:"):
            try:
                return int(target.rsplit(":", 1)[-1])
            except ValueError:
                return None
        return None

    # ---------- команды ----------
    async def cmd_start(self, message: Message):
        if not self._admin_msg(message):
            return
        engine = self.app.engine
        await message.answer(
            "🎛 <b>Панель управления автоответчиком</b>\n\n"
            f"📡 Рабочих аккаунтов: <b>{len(engine.clients)}</b>\n"
            f"⏱ Пауза между ответами: <b>{config.COOLDOWN} сек.</b>\n\n"
            f"<b>Как добавить аккаунт:</b>\n"
            f"• закинь файл <code>accN.session</code> в папку <code>{config.DATA_DIR}</code>\n"
            f"• задай строку <code>ACC{N}_SESSION</code> в переменных окружения\n"
            f"• затем нажми «🔄 Сканировать»\n\n"
            f"У каждого аккаунта — свой текст ответа.",
            reply_markup=kb.main_menu(),
        )

    # ---------- меню ----------
    async def menu_main(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        _PENDING_TEXT.pop(query.from_user.id, None)
        engine = self.app.engine
        await query.answer()
        await query.message.edit_text(
            "🎛 <b>Панель управления</b>\n\n"
            f"📡 Аккаунтов в сети: <b>{len(engine.clients)}</b>\n"
            f"⚙️ Автоответ включён у <b>{sum(1 for s in engine.clients if self.app.cfg.acc(s).get('enabled', True))}</b>\n\n"
            f"Что нужно сделать?",
            reply_markup=kb.main_menu(),
        )

    async def help_show(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        await query.answer()
        await query.message.edit_text(
            "❓ <b>Всё управление — кнопками</b>\n\n"
            "📋 <b>Аккаунты</b> — список; нажми на номер, чтобы открыть панель аккаунта "
            "(вкл/выкл, изменить текст)\n"
            "📝 <b>Текст всем</b> — задать один текст для всех аккаунтов\n"
            "🔍 Сканировать — подключить новые сессии без перезапуска\n"
            "📊 Статус — сводка по системе\n\n"
            "Файлы сессий <code>accN.session</code> клади в <code>/app/data</code> "
            "(на хостинге это папка <code>data/</code>).",
            reply_markup=kb.main_menu(),
        )

    # ---------- статус ----------
    async def st_show(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        engine = self.app.engine
        uptime = int(time.time() - self.app.started)
        days, rem = divmod(uptime, 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        await query.answer()
        await query.message.edit_text(
            "📊 <b>Статус</b>\n\n"
            f"🟢 Онлайн: <b>{len(engine.clients)}</b>\n"
            f"⚙️ Включено автоответов: <b>{sum(1 for s in engine.clients if self.app.cfg.acc(s).get('enabled', True))}</b>\n"
            f"⚠️ Ошибки сессий: <b>{len(engine.errors)}</b>\n"
            f"⏳ Аптайм: <b>{days}д {hours}ч {minutes}м</b>\n\n"
            f"📁 Папка сессий: <code>{config.DATA_DIR}</code>",
            reply_markup=kb.main_menu(),
        )

    # ---------- аккаунты ----------
    async def acc_list(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        try:
            page = max(0, int((query.data or "acc:list:0").rsplit(":", 1)[-1]))
        except ValueError:
            page = 0
        slots = self._slots_known()
        await query.answer()
        if not slots:
            await query.message.edit_text(
                "Аккаунтов пока нет.\n\n"
                f"Закинь файл <code>accN.session</code> в <code>{config.DATA_DIR}</code> "
                "и нажми «🔄 Сканировать».",
                reply_markup=kb.main_menu(),
            )
            return
        total_pages = max(1, (len(slots) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        await query.message.edit_text(
            f"📋 <b>Аккаунты</b> — страница {page + 1}/{total_pages}\n"
            "Нажми на аккаунт, чтобы открыть его панель.",
            reply_markup=self._accounts_markup(slots, page),
        )

    def _accounts_markup(self, slots: list[int], page: int):
        engine = self.app.engine
        return kb.accounts_page(
            slots,
            page,
            PAGE_SIZE,
            state_of=lambda s: bool(self.app.cfg.acc(s).get("enabled", True)),
            name_of=engine.name,
        )

    async def acc_open(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        slot = self._slot_of(query)
        if slot not in self._slots_known():
            await query.answer("Такого аккаунта нет", show_alert=True)
            return
        _CTX[query.from_user.id] = f"slot:{slot}"
        await query.answer()
        await query.message.edit_text(self._account_card(slot), reply_markup=kb.account_panel(slot))

    async def acc_toggle(self, query: CallbackQuery, enabled: bool):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        slot = self._slot_of(query)
        if slot not in self.app.engine.clients:
            await query.answer("Аккаунт не в сети", show_alert=True)
            return
        self.app.cfg.set_enabled([slot], enabled)
        word = "✅ Включён" if enabled else "⛔ Выключен"
        await query.answer()
        await query.message.edit_text(
            f"{self._account_card(slot)}\n\n{word}.",
            reply_markup=kb.account_panel(slot),
        )

    async def acc_on(self, query: CallbackQuery):
        await self.acc_toggle(query, True)

    async def acc_off(self, query: CallbackQuery):
        await self.acc_toggle(query, False)

    # ---------- массовые включения/выключения ----------
    async def all_on(self, query: CallbackQuery):
        await self._toggle_all(query, True)

    async def all_off(self, query: CallbackQuery):
        await self._toggle_all(query, False)

    async def _toggle_all(self, query: CallbackQuery, enabled: bool):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        slots = sorted(self.app.engine.clients)
        if not slots:
            await query.answer("Нет аккаунтов в сети", show_alert=True)
            return
        self.app.cfg.set_enabled(slots, enabled)
        word = "✅ ВСЕ ВКЛЮЧЕНЫ" if enabled else "⛔ ВСЕ ВЫКЛЮЧЕНЫ"
        await query.answer()
        await query.message.edit_text(
            f"{word} ({len(slots)} шт.)",
            reply_markup=kb.toggle_done(),
        )

    # ---------- текст ответа ----------
    async def acc_text(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        slot = self._slot_of(query)
        target = f"slot:{slot}"
        prompt = (
            f"✏️ Отправь сообщение с новым текстом ответа для аккаунта "
            f"<b>{slot}. {self.app.engine.name(slot)}</b>\n\n"
            "Просто напиши текст — он станет автоответом."
        )
        await self._begin_text(query, target, prompt)

    async def text_all(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        prompt = (
            "✏️ Отправь сообщение — оно станет текстом автоответа "
            "для <b>всех</b> аккаунтов.\n\n"
            "Просто напиши текст."
        )
        await self._begin_text(query, ALL, prompt)

    async def _begin_text(self, query: CallbackQuery, target: str, prompt: str):
        _CTX[query.from_user.id] = target
        _PENDING_TEXT[query.from_user.id] = target
        await query.answer()
        await query.message.edit_text(prompt, reply_markup=kb.text_prompt())

    async def edit_again(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        target = _CTX.get(query.from_user.id, ALL)
        if target == ALL:
            await self.text_all(query)
        else:
            slot = self._target_slot(target)
            if slot is None:
                await self.menu_main(query)
                return
            await query.answer()
            await query.message.edit_text(
                f"✏️ Новый текст для аккаунта <b>{slot}. {self.app.engine.name(slot)}</b>\n\n"
                "Просто напиши текст.",
                reply_markup=kb.text_prompt(),
            )
            _PENDING_TEXT[query.from_user.id] = target

    async def cancel_input(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        target = _CTX.get(query.from_user.id, ALL)
        _PENDING_TEXT.pop(query.from_user.id, None)
        await query.answer("Отменено")
        if target != ALL:
            slot = self._target_slot(target)
            if slot is not None:
                await query.message.edit_text(self._account_card(slot), reply_markup=kb.account_panel(slot))
                return
        await query.message.edit_text("Отменено.", reply_markup=kb.main_menu())

    async def catch_text(self, message: Message):
        if not self._admin_msg(message) or not message.text:
            return
        uid = message.from_user.id
        target = _PENDING_TEXT.pop(uid, None)
        if not target:
            return
        text = message.text.strip()
        if not text:
            await message.answer("Пустой текст нельзя. Отправь текст ещё раз.")
            _PENDING_TEXT[uid] = target
            return
        slots = self._set_text_action(target, text)
        if not slots:
            await message.answer("Нет аккаунтов в сети.", reply_markup=kb.main_menu())
            return
        who = ", ".join(f"{s} ({self.app.engine.name(s)})" for s in slots)
        await message.answer(
            f"✅ Текст сохранён для: <b>{who}</b>\n\n{text}",
            reply_markup=kb.text_done(),
        )

    # ---------- сканирование ----------
    async def scan_run(self, query: CallbackQuery):
        if not self._admin_query(query):
            return await query.answer("Нет доступа", show_alert=True)
        await query.answer()
        await query.message.edit_text("🔄 Сканирую сессии...", reply_markup=None)
        started = await self.app.engine.reload()
        engine = self.app.engine
        lines = ["🔄 <b>Сканирование завершено</b>\n"]
        if started:
            for slot, name in sorted(started.items()):
                lines.append(f"✅ {slot}. {name}")
        else:
            lines.append("Новых аккаунтов не найдено.")
        if engine.errors:
            lines.append("\n❌ Ошибки в сессиях:")
            for slot in sorted(engine.errors)[:5]:
                lines.append(f"  {slot}. {engine.errors[slot][:60]}")
        if not self._slots_known():
            lines.append(f"\nФайлов нет. Положи <code>accN.session</code> в <code>{config.DATA_DIR}</code>.")
        await query.message.edit_text("\n".join(lines), reply_markup=kb.scan_result_panel())

    # ---------- заглушка ----------
    async def noop(self, query: CallbackQuery):
        await query.answer()


def setup_handlers(dp: Dispatcher, handlers: Handlers) -> None:
    router = Router()
    router.message.register(handlers.cmd_start, CommandStart())
    router.message.register(handlers.catch_text)

    router.callback_query.register(handlers.menu_main, lambda q: q.data == "menu:main")
    router.callback_query.register(handlers.help_show, lambda q: q.data == "help:show")
    router.callback_query.register(handlers.st_show, lambda q: q.data == "st:show")
    router.callback_query.register(handlers.acc_list, lambda q: q.data and q.data.startswith("acc:list:"))
    router.callback_query.register(handlers.acc_open, lambda q: q.data and q.data.startswith("acc:open:"))
    router.callback_query.register(handlers.acc_on, lambda q: q.data and q.data.startswith("acc:on:"))
    router.callback_query.register(handlers.acc_off, lambda q: q.data and q.data.startswith("acc:off:"))
    router.callback_query.register(handlers.acc_text, lambda q: q.data and q.data.startswith("acc:text:"))
    router.callback_query.register(handlers.all_on, lambda q: q.data == "all:on")
    router.callback_query.register(handlers.all_off, lambda q: q.data == "all:off")
    router.callback_query.register(handlers.text_all, lambda q: q.data == "text:all")
    router.callback_query.register(handlers.edit_again, lambda q: q.data == "edit:again")
    router.callback_query.register(handlers.cancel_input, lambda q: q.data == "cancel:input")
    router.callback_query.register(handlers.scan_run, lambda q: q.data == "scan:run")
    router.callback_query.register(handlers.noop, lambda q: q.data == "noop")
    dp.include_router(router)