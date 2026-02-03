"""Handler for /strategy command - strategic planning session."""

import asyncio
import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from d_brain.bot.formatters import format_process_report
from d_brain.bot.states import StrategyState
from d_brain.config import get_settings
from d_brain.services.processor import ClaudeProcessor
from d_brain.services.transcription import DeepgramTranscriber

router = Router(name="strategy")
logger = logging.getLogger(__name__)


@router.message(Command("strategy"))
async def cmd_strategy(message: Message, state: FSMContext) -> None:
    """Handle /strategy command - start or continue strategic session."""
    user_id = message.from_user.id if message.from_user else 0
    logger.info("Strategy command triggered by user %s", user_id)

    # Set FSM state - stay in strategy mode
    await state.set_state(StrategyState.in_session)

    # First call - no user input, just "continue from where I left off"
    await run_strategy(message, user_input=None, user_id=user_id)


@router.message(StrategyState.in_session)
async def handle_strategy_input(
    message: Message, bot: Bot, state: FSMContext
) -> None:
    """Handle voice/text input during strategy session."""
    user_id = message.from_user.id if message.from_user else 0
    user_input = None

    # Handle /exit to leave strategy mode
    if message.text and message.text.strip().lower() in ("/exit", "/stop", "/cancel"):
        await state.clear()
        await message.answer(
            "👋 Стратегическая сессия приостановлена.\n"
            "Напиши /strategy когда захочешь продолжить."
        )
        return

    # Handle other commands - exit strategy mode and let them through
    if message.text and message.text.startswith("/"):
        await state.clear()
        return  # Let other routers handle the command

    # Handle voice input
    if message.voice:
        await message.chat.do(action="typing")
        settings = get_settings()
        transcriber = DeepgramTranscriber(settings.deepgram_api_key)

        try:
            file = await bot.get_file(message.voice.file_id)
            if not file.file_path:
                await message.answer("❌ Не удалось скачать голосовое")
                return

            file_bytes = await bot.download_file(file.file_path)
            if not file_bytes:
                await message.answer("❌ Не удалось скачать голосовое")
                return

            audio_bytes = file_bytes.read()
            user_input = await transcriber.transcribe(audio_bytes)
        except Exception as e:
            logger.exception("Failed to transcribe voice for /strategy")
            await message.answer(f"❌ Не удалось транскрибировать: {e}")
            return

        if not user_input:
            await message.answer("❌ Не удалось распознать речь")
            return

        # Echo transcription
        await message.answer(f"🎤 <i>{user_input}</i>")

    elif message.text:
        user_input = message.text

    else:
        await message.answer("❌ Отправь текст или голосовое сообщение")
        return

    await run_strategy(message, user_input=user_input, user_id=user_id)


async def run_strategy(
    message: Message,
    user_input: str | None,
    user_id: int = 0,
) -> None:
    """Run strategy processing with Claude."""
    status_msg = await message.answer("⏳ Думаю...")

    settings = get_settings()
    processor = ClaudeProcessor(settings.vault_path, settings.todoist_api_key)

    async def process_with_progress() -> dict:
        task = asyncio.create_task(
            asyncio.to_thread(
                processor.execute_strategy, user_input, user_id
            )
        )

        elapsed = 0
        while not task.done():
            await asyncio.sleep(30)
            elapsed += 30
            if not task.done():
                try:
                    await status_msg.edit_text(
                        f"⏳ Думаю... ({elapsed // 60}m {elapsed % 60}s)"
                    )
                except Exception:
                    pass

        return await task

    report = await process_with_progress()

    formatted = format_process_report(report)
    try:
        await status_msg.edit_text(formatted)
    except Exception:
        await status_msg.edit_text(formatted, parse_mode=None)
