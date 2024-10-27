import config

CHUNK_CUT = '<--------------chunk_cut>---------------->'
CHUNK_SRC = 'chunk_src'
TABLE = "Таблица"
UNNUMBERED_TABLE = "Таблица без номера"
CHUNK_TABLE = 'chunk_table'
CHUNK_TABLE_NAME = 'chunk_table_name'
CHUNK_QUOTE = 'chunk_quote'
CHUNK_NUMBER = 'chunk_number'
CHUNK_TAGS = 'chunk_tags'
CHUNK_META = 'chunk_meta'
CHUNK_IDS = 'chunk_ids'

models_cfg = config.Config('models.cfg')
BEGIN_TAG = models_cfg['begin_tag']
MAIN_MODEL = models_cfg["mainmodel"]


def read_tag(text: str, tag: str) -> str:
    t = text.split(f'</{tag}>')[0]
    t = t.split(f'<{tag}>')
    if len(t)>1:
        t = t[1]
    else:
        t = ""
    return t


def remove_tag(text: str, tag: str) -> str:
    if f'<{tag}>' in text:
        head = text.split(f'<{tag}>')[0]
        tail = text.split(f'</{tag}>')[1]
        return f'{head}{tail}'
    return text


def wrap_by_tag(text: str, tag: str) -> str:
    t = f'<{tag}>\n{text}\n</{tag}>\n'
    return t


def add_tag(text: str, tag: str, tag_body) -> str:
    w = wrap_by_tag(tag_body, tag)
    t = f'{text}\n{w}'
    return t


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
