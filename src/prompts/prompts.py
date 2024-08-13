PROMPTS_RU = {
"DnD_generating_lore":
"""Создай предысторию для приключения Dungeons and Dragons,
включающий следующие элементы:
%s
Не рассказывай ничего о том, что будет происходить в приключении""",
"DnD_init_location":
"""Создай начальную локацию для игры Dungeons and Dragons со следующей предысторией:
%s.
Дай только ту информацию, которые игроки видят вокруг или знают из предыстории.
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
"""Ты ведущий в игре Dungeons and Dragons, смоделируй действие игрока в локации, учитывая недавние действия и их последствия:
Действие игрока:
{action}

Локация:
{location}

Недавние действия:
{recent_actions}.
Ты должен, основываясь на действиях игрока и текущей ситуации, определить, нужно ли проводить проверку (бросок кубика). \
Если да, то определить тип кубика (например, d20) и произвести имитацию броска, после чего сообщить результат и его последствия.""",
"DnD_master":
"""Ответь игроку, базируясь на его локации и недавних действиях и их последствиях.
Фраза игрока: 
{phrase}

Локация: 
{location}

Недавние действия:
{recent_actions}.""",
"extract_hero_data":
"""Создай словарь в формате Python из сообщения, в котором представляется персонаж Dungeons and Dragons, 
содержащее Расу, rраткую предысторию, 2 Навыка, Оружие и Внешний вид. 
Если в сообщении не будет какого-то пункта, добавь его. 
Словарь должен быть следующего формата:
{"name": <имя персонажа>,
  "skill1": <первый навык>,
  "skill2: <второй навык>,
  "weapon": <оружие>,
  "appearance": <внешний вид>
}
Вот сообщение, из которого тебе нужно извлечь данные:
%s
"""
}