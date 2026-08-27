#!/usr/bin/env python3
"""Inline-клавиатуры панели управления (всё управление — кнопками)."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📋 Аккаунты", callback_data="acc:list:0")
    b.button(text="➕ Подключить аккаунт", callback_data="help:add")
    b.button(text="📊 Статус", callback_data="st:show")
    b.button(text="🔄 Сканировать", callback_data="scan:run")
    b.button(text="📝 Текст всем", callback_data="text:all")
    b.button(text="✅ Включить все", callback_data="all:on")
    b.button(text="⛔ Выключить все", callback_data="all:off")
    b.button(text="⚙️ Настройки", callback_data="set:show")
    b.button(text="❓ Помощь", callback_data="help:show")
    b.adjust(2)
    return b.as_markup()


def accounts_page(slots: list[int], page: int, page_size: int = 10,
                  state_of=None, name_of=None) -> InlineKeyboardMarkup:
    """Список аккаунтов с пагинацией. Данные берутся из app.engine/app.cfg."""
    b = InlineKeyboardBuilder()
    total_pages = max(1, (len(slots) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start, end = page * page_size, min((page + 1) * page_size, len(slots))
    for slot in slots[start:end]:
        state = "🟢" if state_of(slot) else "🔴"
        name = (name_of(slot) or f"аккаунт {slot}")[:28]
        b.row(InlineKeyboardButton(
            text=f"{state} {slot}. {name}",
            callback_data=f"acc:open:{slot}",
        ))
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"acc:list:{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"• {page + 1}/{total_pages} •", callback_data="noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"acc:list:{page + 1}"))
        b.row(*nav)
    b.row(InlineKeyboardButton(text="⬅️ Меню", callback_data="menu:main"))
    return b.as_markup()


def account_panel(slot: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Включить", callback_data=f"acc:on:{slot}")
    b.button(text="⛔ Выключить", callback_data=f"acc:off:{slot}")
    b.row(InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"acc:text:{slot}"))
    b.row(InlineKeyboardButton(text="🗑 Удалить аккаунт", callback_data=f"acc:del:{slot}"))
    b.row(InlineKeyboardButton(text="📋 Аккаунты", callback_data="acc:list:0"))
    b.row(InlineKeyboardButton(text="⬅️ Меню", callback_data="menu:main"))
    return b.as_markup()


def confirm_delete(slot: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Да, удалить", callback_data=f"acc:delc:{slot}")
    b.button(text="⬅️ Отмена", callback_data=f"acc:open:{slot}")
    b.adjust(2)
    return b.as_markup()


def settings_panel() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⏱ Изменить паузу", callback_data="set:cool")
    b.button(text="📝 Текст по умолчанию", callback_data="set:def")
    b.row(InlineKeyboardButton(text="⬅️ Меню", callback_data="menu:main"))
    return b.as_markup()


def text_prompt() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✖️ Отмена", callback_data="cancel:input")
    return b.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Меню", callback_data="menu:main")
    return b.as_markup()


def text_done() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Ещё текст", callback_data="edit:again")
    b.button(text="⬅️ Меню", callback_data="menu:main")
    b.adjust(2)
    return b.as_markup()


def toggle_done() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📋 Аккаунты", callback_data="acc:list:0")
    b.button(text="⬅️ Меню", callback_data="menu:main")
    b.adjust(2)
    return b.as_markup()


scan_result_panel = toggle_done