from aiogram.fsm.state import State, StatesGroup


class FSMStates(StatesGroup):
    creating_heroes = State()
    generating_adventure = State()
    DnD_is_adventure_ok_choosing = State()
    DnD_default_state = State()
    DnD_in_mission = State()
    DnD_taking_action = State()
    DnD_took_action = State()
    getting_amount_of_players = State()
    DnD_game_started = State()
