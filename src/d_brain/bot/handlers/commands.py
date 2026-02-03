"""Command handlers for /start, /help, /status."""

from datetime import date
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from d_brain.bot.keyboards import get_main_keyboard
from d_brain.config import get_settings
from d_brain.services.session import SessionStore
from d_brain.services.storage import VaultStorage

router = Router(name="commands")


def _goals_are_empty(vault_path: Path) -> bool:
    """Check if yearly goals still have placeholder text."""
    goals_dir = vault_path / "goals"
    if not goals_dir.exists():
        return True

    for f in goals_dir.glob("1-yearly*.md"):
        content = f.read_text()
        # Template placeholders from the default file
        if "[Your Goal]" in content or "<!-- What" in content:
            return True
        # File exists but has real content
        if "Goal 1:" in content or "##" in content:
            # Check if ANY goal is actually filled (not just headers)
            lines = content.split("\n")
            has_real_goal = any(
                line.strip().startswith("### Goal")
                and "[Your Goal]" not in line
                and line.strip() != "### Goal 1:"
                for line in lines
            )
            if not has_real_goal:
                return True
            return False

    # No yearly goals file at all
    return True


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command.

    If goals are empty (placeholders) — launch strategy session.
    Otherwise — show normal welcome.
    """
    settings = get_settings()

    if _goals_are_empty(settings.vault_path):
        # Goals not filled — start strategy
        await message.answer(
            "👋 <b>Добро пожаловать в d-brain!</b>\n\n"
            "Я вижу, что цели ещё не заполнены.\n"
            "Давай начнём со стратегической сессии — "
            "я помогу тебе сформулировать цели на год за 6 шагов.\n\n"
            "Это займёт несколько сессий, но в итоге бот будет "
            "точно понимать твои приоритеты. 🎯",
            reply_markup=get_main_keyboard(),
        )

        # Auto-launch strategy
        from d_brain.bot.handlers.strategy import cmd_strategy

        await cmd_strategy(message, state)
    else:
        # Normal welcome
        await message.answer(
            "<b>d-brain</b> - твой голосовой дневник\n\n"
            "Отправляй мне:\n"
            "🎤 Голосовые сообщения\n"
            "💬 Текст\n"
            "📷 Фото\n"
            "↩️ Пересланные сообщения\n\n"
            "Всё будет сохранено и обработано.\n\n"
            "<b>Команды:</b>\n"
            "/status - статус сегодняшнего дня\n"
            "/process - обработать записи\n"
            "/do - выполнить произвольный запрос\n"
            "/strategy - стратегическая сессия\n"
            "/weekly - недельный дайджест\n"
            "/help - справка",
            reply_markup=get_main_keyboard(),
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "<b>Как использовать d-brain:</b>\n\n"
        "1. Отправь голосовое — я транскрибирую и сохраню\n"
        "2. Отправь текст — сохраню как есть\n"
        "3. Отправь фото — сохраню в attachments\n"
        "4. Перешли сообщение — сохраню с источником\n\n"
        "Вечером используй /process для обработки:\n"
        "Мысли → Obsidian, Задачи → Todoist\n\n"
        "<b>Команды:</b>\n"
        "/status - сколько записей сегодня\n"
        "/process - обработать записи\n"
        "/do - выполнить произвольный запрос\n"
        "/strategy - стратегическая сессия\n"
        "/weekly - недельный дайджест\n\n"
        "<i>Пример: /do перенеси просроченные задачи на понедельник</i>"
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Handle /status command."""
    user_id = message.from_user.id if message.from_user else 0
    settings = get_settings()
    storage = VaultStorage(settings.vault_path)

    # Log command
    session = SessionStore(settings.vault_path)
    session.append(user_id, "command", cmd="/status")

    today = date.today()
    content = storage.read_daily(today)

    if not content:
        await message.answer(f"📅 <b>{today}</b>\n\nЗаписей пока нет.")
        return

    lines = content.strip().split("\n")
    entries = [line for line in lines if line.startswith("## ")]
    voice_count = sum(1 for e in entries if "[voice]" in e)
    text_count = sum(1 for e in entries if "[text]" in e)
    photo_count = sum(1 for e in entries if "[photo]" in e)
    forward_count = sum(1 for e in entries if "[forward from:" in e)
    total = len(entries)

    # Get weekly stats from session
    week_stats = ""
    stats = session.get_stats(user_id, days=7)
    if stats:
        week_stats = "\n\n<b>За 7 дней:</b>"
        for entry_type, count in sorted(stats.items()):
            week_stats += f"\n• {entry_type}: {count}"

    await message.answer(
        f"📅 <b>{today}</b>\n\n"
        f"Всего записей: <b>{total}</b>\n"
        f"- 🎤 Голосовых: {voice_count}\n"
        f"- 💬 Текстовых: {text_count}\n"
        f"- 📷 Фото: {photo_count}\n"
        f"- ↩️ Пересланных: {forward_count}"
        f"{week_stats}"
    )
