from termcolor import colored
import model_io as mio
import ollama
import sys
import re

NUM_CTX = 8192 # 32768 #2048

# Запрос № 1
query_1 = 'Перечислите перечень испытаний для широкополосного проката (базовое' \
          ' исполнение), марка стали 09Г2С, толщина проката 25, класс прочности' \
          '  325, категория 12 для ГОСТ 19281-2014.'

# Ответ
answer_1 = 'Временное сопротивление, предел текучести, относительное удлинение,' \
           ' ударная вязкость -40 (KCU), ударная вязкость (KCU) мех. старение' \
           ' при комнатной температуре.'


book = []
system_msg = {
                'role': 'system',
                'content': 'Отвечай одним словом, какой вид проката упоминается в тексте'
             }
user_msg = {
                'role': 'user',
                'content': query_1
           }
book.append(system_msg)
# book.append(user_msg)
models_config_file = 'models.cfg'

# where_cond = {"$and": [{"category": "chroma"}, {"author": "john"}]}
def rag2(context, where_dict, show=False):
    collection = mio.get_collection('metalloprokat')
    n_res = 5
    sz = 0
    limit = 200
    while sz < NUM_CTX and n_res < limit:
        sz = 0
        relevant_docs = collection.query(query_texts=(context),
                                         n_results=n_res,
                                         where=where_dict)
        rag_context = relevant_docs["documents"][0]

        for c in rag_context:
            sz += len(c)
        n_res += 1
    print(f"RAG volume = {sz}")
    print(f"RAG list len = {len(rag_context)}")
    if show:
        print(colored(f'rag docs<{rag_context}>', 'green'))
    return rag_context


def rag(context, meta_key: str = "", meta_value: str = "", show=False):
    collection = mio.get_collection('metalloprokat')
    n_res = 5
    sz = 0
    limit = 200
    while sz < NUM_CTX and n_res < limit:
        sz = 0
        relevant_docs = collection.query(query_texts=(context),
                                         n_results=n_res,
                                         where={ meta_key: meta_value})
        rag_context = relevant_docs["documents"][0]

        for c in rag_context:
            sz += len(c)
        n_res += 1
    print(f"RAG volume = {sz}")
    print(f"RAG list len = {len(rag_context)}")
    if show:
        print(colored(f'rag docs<{rag_context}>', 'green'))
    return rag_context


def ai(prompt_txt: str, show=False) -> str:
    if show:
        print(colored(f"promt: {prompt_txt}", 'light_yellow'))
    opt = {"temperature": 0, "num_ctx": NUM_CTX}
    stream = ollama.generate(model='llama3.1', prompt=prompt_txt, options=opt)
    res = stream["response"].removesuffix('.')
    print(colored(f'>>> {res}\n', 'yellow'))
    return res


def clean_up_tables_list(tables_string: str) -> list[str]:
    tables_string = tables_string.replace('[', '')
    tables_string = tables_string.replace(']', '')
    tables_string = tables_string.replace('Таблицы', '')
    tables_string = tables_string.split(',')
    tables_string = [s.strip() for s in tables_string]
    return tables_string

"""
Вопросы к ИИ
1. Какой тип проката в запросе?
1. Какое исполнение?
1. Марка стали?
1. Толщина?
1. Класс прочности?
1. Категория?
1. Номер ГОСТа? 
1. Какие таблицы ГОСТа относятся к (тип + исп) прокату?
1. Среди выбранных таблиц какие упоминают такие класс прочности и марку стали?
1. Какие сведения соответствуют толщине  и категории?
"""
print(colored("Разбор запроса", "red"))

GOST_NUM = 'gost_num' # Key name.
TABLE_NUMBER = 'table_number'
qwe = {}


# Получаем тип проката
prompt = f"Какой тип проката упомянут в тексте: {query_1} Ответь двумя словами."
qwe['prokat_type'] = ai(prompt)
print('prokat_type:', qwe['prokat_type'])

# Получаем название ГОСТа
prompt = f"Изучи текст: {query_1} Какой " \
         " ГОСТ в нем упомянут? Выведи только обозначение ГОСТа."
res = ai(prompt)
prompt = f'Извлеки из текста обозначение ГОСТа. Вот из этого текста: {res}'
gost = ai(prompt, show=True)
qwe[GOST_NUM] = gost.split('-')[0]
print('GOST Num:', qwe[GOST_NUM])
qwe['gost_year'] = gost.split('-')[1]
print('GOST Year:', qwe['gost_year'])


# Получаем исполнение проката
prompt = f'Какое исполнение упомянуто в тексте: "{query_1}"' \
          '  Ответь одним словом.'

qwe['prokat_option'] = ai(prompt, show=True)
print('prokat_option:', qwe['prokat_option'])

# Проверяем, что в ГОСТе упоминается это исполнение проката
docs = rag('исполнение, исполнения', GOST_NUM, qwe[GOST_NUM], show=True)

opt = qwe['prokat_option']
prompt = f'В этом тексте: {docs}, встречается исполнение "{opt}"? Ответь коротко.'
prokat_option_in_gost = ai(prompt, show=True)
if 'да' in prokat_option_in_gost.lower():
    qwe['option_in_gost'] = True
else:
    qwe['option_in_gost'] = False

# Получаем марку стали
prompt = f'Какая марка стали упомянута в тексте: "{query_1}"' \
          '  Ответь одним словом.'
qwe['steel'] = ai(prompt, show=True)

# Проверяем, что в ГОСТе упоминается эта марка стали
docs = rag('сталь', GOST_NUM, qwe[GOST_NUM], show=True)
opt = qwe['steel']
prompt = f'В этом тексте: "{docs}", встречается марка стали "{opt}"? Ответь коротко.'
steel_mark_in_gost = ai(prompt, show=True)
if 'да' in steel_mark_in_gost.lower():
    qwe['steel_in_gost'] = True
else:
    qwe['steel_in_gost'] = False

# Получаем толщину проката
prompt = f'Какая толщина упомянута в тексте: "{query_1}"' \
          '  Ответь одним словом.'
qwe['thickness'] = ai(prompt, show=True)

# Проверяем, что в ГОСТе упоминается эта толщина проката
docs = rag('толщина', GOST_NUM, qwe[GOST_NUM], show=True)
opt = qwe['thickness']
prompt = f'В этом тексте: "{docs}", встречается толщина проката "{opt}"? Ответь коротко.'
res = ai(prompt, show=True)
if 'да' in res.lower():
    qwe['thickness_in_gost'] = True
else:
    qwe['thickness_in_gost'] = False

# Получаем класс прочности проката
prompt = f'Какой класс прочности упомянут в тексте: "{query_1}"' \
          '  Ответь одним словом.'
qwe['solidity'] = ai(prompt, show=True)

# Проверяем, что в ГОСТе упоминается этот класс прочности
docs = rag('класс прочности', GOST_NUM, qwe[GOST_NUM], show=True)
opt = qwe['solidity']
prompt = f'В этом тексте: "{docs}", встречается класс прочности "{opt}"? Ответь коротко.'
res = ai(prompt, show=True)
if 'да' in res.lower():
    qwe['solidity_in_gost'] = True
else:
    qwe['solidity_in_gost'] = False

# Получаем категорию проката
prompt = f'Какая категория упомянута в тексте: "{query_1}"' \
          '  Ответь коротко.'
res = ai(prompt, show=True)
prompt = f'"Извлеки число из этого текста: "{res}"'
qwe['category'] = ai(prompt, show=True)

# Проверяем, что в ГОСТе упоминается эта категория проката
docs = rag('категория', GOST_NUM, qwe[GOST_NUM], show=True)
opt = qwe['category']
prompt = f'В этом тексте: "{docs}", встречается категория "{opt}"? Ответь коротко.'
res = ai(prompt, show=True)
if 'да' in res.lower():
    qwe['category_in_gost'] = True
else:
    qwe['category_in_gost'] = False

# Находим таблицы с нужной категорией
opt = qwe['category']
docs = rag(f'категория {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается' \
         f' категория "{opt}"? Ответь коротко.'
res = ai(prompt, show=True)

prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко.'
res = ai(prompt, show=True)
res = clean_up_tables_list(res)
qwe['category_in_tables'] = res

# Находим таблицы с нужной сталью
opt = qwe['steel']
docs = rag(f'сталь {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается сталь' \
          f' "{opt}"?' \
          ' Ответь коротко.'
res = ai(prompt, show=True)

prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко.'
res = ai(prompt, show=True)
res = clean_up_tables_list(res)
qwe['steel_in_tables'] = res

# Находим таблицы с нужным классом прочности
opt = qwe['solidity']
docs = rag(f'класс прочности {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается класс прочности' \
          f' "{opt}"?' \
          ' Ответь коротко.'
res = ai(prompt, show=True)

prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко.'
res = ai(prompt, show=True)
res = clean_up_tables_list(res)
qwe['solidity_in_tables'] = res

# Находим таблицы с нужным типом проката
opt = qwe['prokat_type']
docs = rag(f'тип проката {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается тип проката' \
          f' "{opt}"?' \
          ' Ответь коротко.'
res = ai(prompt, show=True)

prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко.'
res = ai(prompt, show=True)
res = clean_up_tables_list(res)
qwe['type_in_tables'] = res

# Находим таблицы с нужным исполнением
opt = qwe['prokat_option']
docs = rag(f'исполнение проката {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается исполнение проката' \
          f' "{opt}"?' \
          ' Ответь коротко.'
res = ai(prompt, show=True)

prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко. Перечисли через запятую.'
res = ai(prompt, show=True)
res = clean_up_tables_list(res)
qwe['prokat_option_in_tables'] = res

# where = {"$and": [{"category": "chroma"}, {"$or": [{"author": "john"}, {"author": "jack"}]}]}
# where_cond = {"$and": [{"category": "chroma"}, {"author": "john"}]}
#'gost_num': '19281', 'gost_year': '2014', 'type': 'table_body', 'table_number': '1'}
where_dict = {"$and": [{"gost_num": "19281"},{"$or": [{"table_number": "5"}, 
              {"table_number": "6"}, {"table_number": "11"},
              {"table_number": "12"}]}]}
docs = rag2(f'исполнение проката {opt} таблица', where_dict=where_dict,
            show=True)
tables = qwe["prokat_option_in_tables"] 
tables.extend(qwe['solidity_in_tables']) 
tables.extend(qwe['steel_in_tables']) 
tables.extend(qwe['type_in_tables']) 
tables.extend(qwe['category_in_tables']) 
prompt = f'Из текста "{docs}" Перечисли перечень испытаний' \
         f' для {qwe["prokat_type"]} проката с исполнением' \
         f' {qwe["prokat_option"]} из стали {qwe["steel"]}' \
         f' класс прочности {qwe["solidity"]} категория {qwe["category"]}' \
         f' толщина {qwe["thickness"]}?'
res = ai(prompt, show=True)

print(qwe)
exit(0)
