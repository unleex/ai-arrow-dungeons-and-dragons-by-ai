PROMPTS_RU = {
"DnD_generating_lore":
"""Создай предысторию для приключения Dungeons and Dragons,
включающий следующие элементы:
%s
Не рассказывай ничего о том, что будет происходить в приключении""",
"DnD_init_location":
"""Создай начальную локацию для игры Dungeons and Dragons со следующей предысторией:
%s
""",
"DnD_generating_mission":
"""Создай задание для игры Dungeons and Dragons со следующей предысторией:
{lore}.

Чтобы она продолжала сюжет. Вот недавние события:
{recent_actions}

Она должна проходить в слеюущей локации:
{location}.
""",
"DnD_taking_action":
"""Смоделируй действие игрока в локации, учитывая недавние действия и их последствия:
Действие игрока: 
{action}

Локация: 
{location}

Недавние действия:
{recent_actions}.
Опиши, что произошло после совершаемого действия.""",
"DnD_master":
"""Ответь игроку, базируясь на его локации и недавних действиях и их последствиях.
Фраза игрока: 
{phrase}

Локация: 
{location}

Недавние действия:
{recent_actions}."""
}