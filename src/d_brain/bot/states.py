"""Bot FSM states."""

from aiogram.fsm.state import State, StatesGroup


class DoCommandState(StatesGroup):
    """States for /do command flow."""

    waiting_for_input = State()  # Waiting for voice or text after /do


class StrategyState(StatesGroup):
    """States for /strategy command flow."""

    in_session = State()
