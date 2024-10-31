import config
import re

CHUNK_CUT = '<--------------chunk_cut>---------------->'
CHUNK_SRC = 'chunk_src'
TABLE = "Таблица"
UNNUMBERED_TABLE = "Таблица без номера"
CHUNK_TABLE = 'chunk_table'
CHUNK_TABLE_NAME = 'chunk_table_name'
CHUNK_TABLE_NUMBER = 'chunk_table_number'
CHUNK_QUOTE = 'chunk_quote'
CHUNK_NUMBER = 'chunk_number'
CHUNK_TAGS = 'chunk_tags'
CHUNK_META = 'chunk_meta'
CHUNK_IDS = 'chunk_ids'
CHUNK_TYPE_PARAGRAPH = 'paragraph'
CHUNK_TYPE_TABLE_BODY = 'table_body'
CHUNK_TYPE_TABLE_DESCRIPTION = "table_description"

models_cfg = config.Config('models.cfg')
BEGIN_TAG = models_cfg['begin_tag']
MAIN_MODEL = models_cfg["mainmodel"]


def read_tag(text: str, tag: str) -> str:
    t = text.split(f'</{tag}>')[0]
    t = t.split(f'<{tag}>')
    if len(t) > 1:
        t = t[1]
    else:
        t = ""
    return t


def remove_tag(text: str, tag: str) -> str:
    """Remove tag and it's data."""

    if f'<{tag}>' in text:
        head = text.split(f'<{tag}>')[0]
        tail = text.split(f'</{tag}>')[1]
        return f'{head}{tail}'
    if f'<{tag}' in text:  # Случай когда тэг не имеет закрывающего парного тэга.
        pattern = rf'<{tag}.*>'
        return re.sub(pattern, '', text)
    
    return text


def wrap_by_tag(text: str, tag: str) -> str:
    t = f'<{tag}>\n{text}\n</{tag}>\n'
    return t


def unwrap_from_tag(text: str, tag: str) -> str:
    t = text.replace(f'<{tag}>', '')
    t = t.replace(f'</{tag}>', '')
    return t


def add_tag(text: str, tag: str, tag_body) -> str:
    w = wrap_by_tag(tag_body, tag)
    t = f'{text}\n{w}'
    return t


def is_tag_in_text(text: str, tag: str) -> bool:
    if f'<{tag}>' in text:
        return True
    else:
        return False


def read_gost_number_year(doc_name):
    value = doc_name.split('ГОСТ')
    digits = value[1].split(' ')
    parts = digits[1].split('-')
    number = parts[0]
    year = parts[1]
    return number, year


def read_table_number(table_name):
    value = table_name.split(TABLE)
    digits = value[1].split(' ')
    number = digits[1]
    return number


def extract_first_table_info(text: str) -> tuple[str, str]:
    # Регулярное выражение для поиска первой строки, начинающейся с 'Таблица',
    # за которой следует пробел, идентификатор таблицы (число или буква + точка + число),
    # еще один пробел и имя таблицы
    #pattern = r'^Таблица\s+((?:\d+)|(?:[a-zA-Z]\.\d+))\s+(.*)$'
    pattern = r'^Таблица\s+((?:\d+)|(?:[а-яА-Я]\.\d+))\s+(.*)$' 
    # Находим первое совпадение в тексте
    match = re.search(pattern, text, flags=re.MULTILINE)

    if match:
        table_id = match.group(1)
        table_name = match.group(2).split('|')[0]
        return table_id, table_name
    else:
        return None, None  # Если совпадений нет, возвращаем None


def add_table_meta(bag, table: dict, gost_num, gost_year):
    chunk_type = 'table_meta' 
    table_number = "undefined"
    table_name = UNNUMBERED_TABLE
    buf = ''
    buf = f'{buf}\n{CHUNK_CUT}'
    print(f'table: {table}')
    t_number, t_name = extract_first_table_info(table['Название таблицы'])
    if t_number is not None:
        table_number = t_number.upper()
        table_name = t_name
    t = wrap_by_tag(table_number, CHUNK_TABLE_NUMBER)
    res = f'{t}'
    t = wrap_by_tag(table_name, CHUNK_TABLE_NAME)
    res = f'{t}\n{res}'
    t = wrap_by_tag(f'{table}\n', CHUNK_TABLE)
    buf = f'{buf}\n{t}\n{res}'
    metas = {'gost_num': gost_num, 'gost_year': gost_year,
             'type': chunk_type, 'table_number': table_number}
    buf = add_tag(buf, CHUNK_META, f'{metas}')
    bag.append(buf)
