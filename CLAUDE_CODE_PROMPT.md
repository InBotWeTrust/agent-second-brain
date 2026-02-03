# Промпт для Claude Code

> Скопируй всё ниже и вставь в Claude Code, находясь в корне проекта.
> Предварительно положи файлы из пакета (SKILL.md, handlers/strategy.py,
> handlers/commands.py, processor_patch.py) в корень проекта или в
> отдельную папку (например `_strategy_integration/`).

---

Интегрируй новый skill "strategy-builder" в проект. Файлы для интеграции лежат в корне проекта (или в папке `_strategy_integration/`).

## Что сделать:

### 1. Положить SKILL.md
Скопируй `SKILL.md` в `vault/.claude/skills/strategy-builder/SKILL.md`

### 2. Положить handler
Скопируй `handlers/strategy.py` в `src/d_brain/bot/handlers/strategy.py`

### 3. Заменить commands.py
Замени `src/d_brain/bot/handlers/commands.py` на `handlers/commands.py` из пакета. Ключевое изменение: /start теперь проверяет goals/ и автоматически запускает стратегию если goals пустые.

### 4. Добавить методы в processor.py
Открой `processor_patch.py` — там 3 метода для класса ClaudeProcessor:
- `_load_strategy_skill()` — положи после `_load_todoist_reference()`
- `_load_strategy_context()` — положи после `_load_strategy_skill()`
- `execute_strategy()` — положи после `execute_prompt()`

Обрати внимание: это код внутри класса (с self). Не потеряй отступы.

### 5. Добавить FSM-состояние
В `src/d_brain/bot/states.py` добавь:

```python
class StrategyState(StatesGroup):
    """States for /strategy command flow."""
    in_session = State()
```

### 6. Добавить кнопку
В `src/d_brain/bot/buttons.py` добавь обработчик для "🎯 Стратегия" — по аналогии с другими кнопками. Вызывает `cmd_strategy` из `handlers/strategy`.

### 7. Добавить в клавиатуру
В файле с `get_main_keyboard()` (или где создаётся `ReplyKeyboardMarkup`) добавь кнопку `"🎯 Стратегия"`.

### 8. Зарегистрировать роутер
Найди где `dp.include_router(...)` и добавь:
```python
from d_brain.bot.handlers import strategy
dp.include_router(strategy.router)
```
ВАЖНО: strategy.router должен быть ПЕРЕД любыми catch-all handlers.

### 9. CLAUDE.md
В таблицу Available Skills: `| strategy-builder | Onboarding + strategic goal-setting (7 steps) |`
В таблицу Quick Commands: `| /strategy | Strategic planning session |`

### 10. Создай директорию
`mkdir -p vault/strategy`

## Правила:
- НЕ рефактори существующий код
- НЕ меняй то, что работает
- Только добавляй новое и заменяй commands.py
- Проверь что все импорты корректны
- Убедись что StrategyState импортируется в strategy.py и commands.py
