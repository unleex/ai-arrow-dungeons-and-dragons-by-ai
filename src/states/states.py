from aiogram.fsm.state import State, StatesGroup


class FSMStates(StatesGroup):
    DnD_init = State()
    DnD_is_adventure_ok_choosing = State()