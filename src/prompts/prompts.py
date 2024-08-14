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
"""Создай начальную локацию для игры Dungeons and Dragons, 
опираясь на следующую предысторию приключения:
%s.
Расскажи героям то, что они видят от лица Dungeon Master.
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
смоделируй действие персонажа в локации, учитывая недавние действия и их последствия, а также его характеристики:
Действие игрока:
{action}

Характеристики игрока и локация:
{hero_data}

Недавние действия:
{recent_actions}.

Ты должен, основываясь на действиях игрока и текущей ситуации, определить, нужно ли проводить проверку (бросок кубика). 
Действие требует проверки, если оно удовлетворяет условию одного из приведенных ниже типов проверки.
Если игрок хочет совершить действие, которое он не может совершить, 
например, если он не обладает каким-то предметом или находится в неподходящей локации, действие сразу считается неуспешным

Вот типы проверок и ситуации, требующие их:
Сила - попытки поднять, толкнуть, подтянуть или сломать что-то, попытки втиснуть своё тело в некое пространство, грубая сила
Ловкость - попытка перемещаться ловко, быстро или тихо, либо попытку не упасть с шаткой опоры
Интеллект - использование логики, образования, памяти или дедуктивного мышления, заклинания.  
Мудрость - попытка понять язык тела, понять чьи-то переживания, заметить что-то в окружающем мире или позаботиться о раненом.

Если удовлетворяет, то определить тип проверки и произвести имитацию броска 
кубика к20 (результаты могут быть от 1 до 20 включительно). 
Если бросок больше 10, то действие успешно, если нет, то неуспешно.
Если не удовлетворяет, то сразу смоделировать действие.

Твой ответ должен включать только процесс действия и результат, а также результат броска кубика, если он потребовался
""",
"DnD_master":
"""Ответь персонажу, базируясь на его локации, характеристиках и недавних действиях и их последствиях.
Фраза игрока: 
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
Если игра окончена, то отправь "1", а со следующей строчки описание концовки игры, 
что случилось с локацией и ее населением.
Если игра может продолжаться, отправь единственный символ: "0"
""",
"update_after_action":
"""Обнови и словарь с данными игрока после его действия. 
Смени значение ключа "location" на новую локацию, если произошло одно из следуюшего:
- игрок перешел в другую локацию
- игрок изменил вид локации, например, сломал или построил что-то
Если игрок поел, прибавь к значению "health" в словаре игрока значение от 1 до 30, 
в зависимости от обилия еды, где 1 - один кусочек, а 30 - плотный обед.
Если игрок получил медицинскую помощь, к значению "health" в словаре игрока значение от 30 до 60,  
где 30 – бинтование ран, а 60 – сильные заклинания исцеления от болезней.
Если игрок получил урон, отними от значения "health" в словаре игрока значение от 1 до 100,
где 1 - царапина, 50 - тяжелые ранения, а 100 - смерть. 
Если игрок сменил оружие, то поставь характеристики нового оружия в ключ "weapon".
Если игрок сменил внешний вид, то новый внешний вид поставь в ключ "appearance".

Вот действие игрока:
{action}.
Вот данные игрока:
{hero_data}

Ответ пришли в формате Python-словаря, имеющий те же ключи, что и изначальный словарь пользователя.
""",
"next_turn":
"""Обнови окружение игроков, соблюдая предысторию приключения и учитывая недавние действия игроков. 
Скажи, что сделали существа в локации, что произошло.


Вот недавние действия игроков:
{recent_actions}

Вот предыстория:
{lore}

Скажи, что изменилось вокруг игроков.
"""
}