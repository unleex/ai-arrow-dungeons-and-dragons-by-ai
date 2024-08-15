PROMPTS_RU = {
"DnD_generating_lore":
"""Создай предысторию для приключения Dungeons and Dragons,
включающий следующие элементы:
%s
Также предыстория должна включать следующее:
- антагонист, его описание и намерения
- локация, природа и фауна, ландшафт
Не рассказывай ничего о том, что будет происходить в приключении
""",
"DnD_init_location":
"""Создай начальную локацию для игры Dungeons and Dragons и опиши ее как Dungeon Master,
опираясь на следующую предысторию приключения:
%s.
Пришли ответ в виде Python-словаря следующего формата:
{
  "location":  <краткое описание локации>,
  "explanation": <четыре предложения с развернутым описанием локации для игроков>
}
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
"""Ты ведущий в игре Dungeons and Dragons,
смоделируй действие персонажа в локации с определенной успешностью, учитывая недавние действия и их последствия, а также его характеристики.
Пункт "успех действия" означает, насколько успешно персонаж совершит действие,
где 1 - персонаж полностью провалил действие, 10 - персонаж сделал его еле-как, а 20 - сделал его блестяще.

Действие игрока:
{action}

Данные игрока и локация:
{hero_data}

Недавние действия:
{recent_actions}.

Успешность действия:
{successful}


Твой ответ должен включать только процесс действия и результат.
""",
"action_is_roll_required":
"""
Ты должен, основываясь на действиях игрока и текущей ситуации, определить, нужно ли проводить проверку (бросок кубика)
и может ли персонаж совершить действие. 
Действие требует проверки, если оно удовлетворяет условию одного из приведенных ниже типов проверки.
Игрок может совершить действие, основываясь на своем опыте и знаниях. Если игрок собирается совершить то, информации о чем
не было в недавних действиях или в его данных, то действие не требует проверки, и не может быть совершено 

Вот типы проверок и ситуации, требующие их:

Силу - попытки поднять, толкнуть, подтянуть или сломать что-то, попытки втиснуть своё тело в некое пространство, грубая сила
Ловкость - попытка перемещаться ловко, быстро или тихо, либо попытку не упасть с шаткой опоры
Интеллект - использование логики, образования, памяти или дедуктивного мышления, заклинания.  
Мудрость - попытка понять язык тела, понять чьи-то переживания, заметить что-то в окружающем мире или позаботиться о раненом.

Если действие не требует проверки, отправь единственный символ: 0. 
Если действие не может быть совершено, отправь -1, а со следующей строчки объясни персонажу причину, почему это действие не является возможным. 
Иначе, отправь единственное слово - тип проверки.

Действие игрока:
{action}

Характеристики игрока и локация:
{hero_data}

Недавние действия:
{recent_actions}.

""",
"DnD_master":
"""
Ты — ведущий в D&D. Отвечай от его лица. Твоя задача — ответить на вопрос игрока. Тебе не нужно продолжать игру, просто дайт ответ на его запрос. Отвечай максимально кратко. Желательно чтобы твой ответ состоял из одного или двух предложений.
Вопрос игрока:
{phrase}

Характеристики и локация:
{hero_data}

Недавние действия:
{recent_actions}.

Вот информация, которую ты вправе давать персонажу:
- то, что персонаж видит вокруг
- результат простого действия персонажа, которое не требует усилий, особых знаний, и времени
- ответ существа (не игрока), которое находится рядом и умеет общаться с игроком (знает его язык)
Если игрок спрашивает то, чего ты не вправе дать, скажи, что не можешь ничего сказать
""",
"extract_hero_data":
"""Создай словарь в формате Python из сообщения игрока, в котором он представляет свой персонаж Dungeons and Dragons,
содержащее имя, Расу, краткую предысторию, 2 Навыка, Оружие и Внешний вид.
Словарь должен быть следующего формата:
{ "name": <имя персонажа>,
  "skill1": <первый навык>,
  "skill2: <второй навык>,
  "weapon": <оружие>,
  "appearance": <внешний вид>
}
Если в сообщении не будет какого-то пункта, добавь его, основываясь на сообщении игрока.
Вот сообщение игрока, из которого тебе нужно извлечь данные:
%s
""",
"is_game_finished":
"""Тебе дано действие игрока. Определи, закончилась ли игра, 
учитывая ее предысторию, локацию, характеристики игрока в формате Python-словаря и недавние действия игроков. 
Предыстория: 
{lore}

Характеристики игрока и локация:
{hero_data}

Недавние действия:
{recent_actions}

Вот признаки окончания игры:
- убит главный антагонист
- убиты все игроки
- уничтожена локация
- антагонист совершил свое злодейство. 
Если соблюден хоть один признак, то отправь 1, а со следующей строчки описание концовки игры, 
что случилось с локацией и ее населением.
Иначе, отправь единственный символ: 0
""",
"update_after_action":
"""Обнови и словарь с данными игрока после его действия. 
Смени значение ключа "location" на новую локацию, если произошло одно из следуюшего:
- игрок перешел в другую локацию
- игрок изменил вид локации, например, сломал или построил что-то
Если игрок сменил оружие, то поставь характеристики нового оружия в ключ "weapon".
Если игрок сменил внешний вид, то новый внешний вид поставь в ключ "appearance".
Также, определи изменение здоровья игрока. Создай ключ "health_diff" 
в словаре, и запиши туда значение от -100 до 100, которое значит, насколько изменилось здоровье.

Вот примеры изменения здоровья:
100 -  персонажа возродили мощным заклинанием
60 - персонажа вылечили от тяжелой болезни сердца или дали мощный антидот от яда
30 - персонаж плотно поел или хорошо поспал
10 - персонаж подлатал раны бинтами
1 - персонаж съел яблоко
-1 - персонаж поцарапался или получил занозу
-10 - персонажа ударили ногой
-30 - персонаж упал с балкона
-60 - персонажа ударили ножом
-100 - на персонажа упала скала или он убит мощным заклинанием

Вот действие игрока:
{action}.

Вот данные игрока:
{hero_data}

Недавние действия:
{recent_actions}

Ответ пришли в формате Python-словаря c указанными ключами
""",
"next_turn":
"""Обнови окружение игроков, соблюдая предысторию приключения и учитывая недавние действия игроков. 
Скажи, что сделали существа в локации, что произошло.

Вот недавние действия игроков:
{recent_actions}

Вот предыстория:
{lore}

Скажи, что изменилось вокруг игроков.
""",
"action_invalid":
""""""
}