# Интеграция strategy-builder в agent-second-brain

## Что в пакете

| Файл | Назначение |
|------|-----------|
| `SKILL.md` | Skill-инструкция для Claude Code (кладётся в vault) |
| `handlers/strategy.py` | Обработчик /strategy (FSM-режим) |
| `handlers/commands.py` | Обновлённый /start с авто-запуском стратегии |
| `processor_patch.py` | Метод execute_strategy() для ClaudeProcessor |
| `CLAUDE_CODE_PROMPT.md` | Промпт для Claude Code — сделает всю интеграцию |
| `INTEGRATION.md` | Этот файл — описание что куда |

## Способ интеграции

### Вариант A — Claude Code (рекомендуется)

1. Форкнуть и клонировать проект
2. Положить все файлы из этого пакета в корень проекта
3. Открыть Claude Code в терминале проекта
4. Скопировать содержимое `CLAUDE_CODE_PROMPT.md` и вставить
5. Claude Code сам внесёт все изменения

### Вариант B — вручную

Смотри раздел «Ручная интеграция» ниже.

---

## Как это работает после интеграции

```
Пользователь нажимает Start в Telegram
            │
            ▼
    cmd_start() проверяет goals/
            │
     ┌──────┴──────┐
     │ goals пустые │ goals заполнены │
     ▼              ▼
  Привет +       Обычное
  авто-запуск    приветствие
  /strategy
     │
     ▼
  Step 0: Знакомство (3 блока вопросов)
     │ → saves about.md
     ▼
  Step 1: Painted Picture (письмо из будущего)
     │ → saves strategy/painted-picture.md
     ▼
  Step 2: Wishes (извлечение + оценка)
     │ → saves strategy/wishes.md
     ▼
  Step 3: WOOP (цели + препятствия + планы)
     │ → saves strategy/woop.md
     │ → FILLS goals/1-yearly-YYYY.md ← КЛЮЧЕВОЙ МОМЕНТ
     ▼
  Step 4: Quarterly Goals (Q1-Q4)
     │ → saves strategy/quarterly.md
     │ → fills goals/2-monthly.md
     ▼
  Step 5: Key Tasks (декомпозиция Q1)
     │ → creates Todoist tasks (label: strategy-q1)
     │ → fills goals/3-weekly.md
     ▼
  Step 6: Control Points (метрики)
     │ → saves strategy/metrics.md
     │ → updates Progress Dashboard
     ▼
  🎉 Стратегия готова!
  /process теперь работает с реальными целями
```

Пользователь может остановиться на любом шаге (/exit)
и продолжить позже (/strategy). Прогресс в strategy/progress.md.

---

## Ручная интеграция

### 1. SKILL.md → vault/.claude/skills/strategy-builder/SKILL.md

### 2. strategy.py → src/d_brain/bot/handlers/strategy.py

### 3. commands.py → заменить src/d_brain/bot/handlers/commands.py

### 4. processor_patch.py → добавить методы в processor.py

В `src/d_brain/services/processor.py` в класс ClaudeProcessor:
- Скопировать `_load_strategy_skill()` и `_load_strategy_context()` после `_load_todoist_reference()`
- Скопировать `execute_strategy()` после `execute_prompt()`

### 5. states.py — добавить

```python
class StrategyState(StatesGroup):
    """States for /strategy command flow."""
    in_session = State()
```

### 6. buttons.py — добавить

```python
@router.message(F.text == "🎯 Стратегия")
async def btn_strategy(message: Message, state: FSMContext) -> None:
    from d_brain.bot.handlers.strategy import cmd_strategy
    await cmd_strategy(message, state)
```

### 7. Keyboard — добавить кнопку "🎯 Стратегия"

### 8. Router — зарегистрировать

```python
from d_brain.bot.handlers import strategy
dp.include_router(strategy.router)
```

### 9. CLAUDE.md — добавить 2 строки в таблицы

### 10. Создать vault/strategy/
