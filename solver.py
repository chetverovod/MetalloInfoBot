from termcolor import colored
import model_io as mio
import ollama
import sys
import re
import config

NUM_CTX = 8192 # 32768 #2048
DEFAULT_SETTINGS_FILE = 'models.cfg'
cfg = config.Config(DEFAULT_SETTINGS_FILE)
COLLECTION_NAME = cfg['collection_name']

# Dictionary key names.
PROKAT_TYPE = 'prokat_type'
GOST_NUM = 'gost_num'
GOST_YEAR = 'gost_year'
OPTION = 'option' # исполнение
OPTION_IN_DOC = 'option_in_doc'
OPTION_IN_TABLES = 'option_in_tables'
CATEGORY = 'category'
CATEGORY_IN_DOC = 'category_in_doc'
CATEGORY_IN_TABLES = 'category_in_tables'
TABLE_NUMBER = 'table_number'
STEEL = 'steel'
STEEL_IN_DOC = 'steel_in_doc'
STEEL_IN_TABLES = 'steel_in_tables'
THICKNESS = 'thickness'
THICKNESS_IN_DOC = 'thickness_in_doc'
TYPE_IN_TABLES = 'type_in_tables'
SOLIDITY = 'solidity'
SOLIDITY_IN_DOC = 'solidity_in_doc'
SOLIDITY_IN_TABLES = 'solidity_in_tables'
TABLES_OF_INTEREST = 'tables_of_interest'
ANSWER = 'answer'


def rag_with_where(context, where_dict, show=False):
    collection = mio.get_collection(COLLECTION_NAME)
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
    collection = mio.get_collection(COLLECTION_NAME)
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
    tables_string = tables_string.replace('Таблица', '')
    tables_string = tables_string.split(',')
    tables_string = [s.strip() for s in tables_string]
    return tables_string


def answering_machine(question: str) -> dict:
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
    
    qwe = {}
    
   # Получаем тип проката
    prompt = f"Какой тип проката упомянут в тексте: {question} Ответь двумя словами."
    qwe[PROKAT_TYPE] = ai(prompt)
    print(PROKAT_TYPE, qwe[PROKAT_TYPE])
    
    # Получаем название ГОСТа
    prompt = f"Изучи текст: {question} Какой " \
             " ГОСТ в нем упомянут? Выведи только обозначение ГОСТа."
    res = ai(prompt)
    prompt = f'Извлеки из текста обозначение ГОСТа. Вот из этого текста: {res}'
    gost = ai(prompt, show=True)
    qwe[GOST_NUM] = gost.split('-')[0]
    print('GOST Num:', qwe[GOST_NUM])
    qwe[GOST_YEAR] = gost.split('-')[1]
    print('GOST Year:', qwe[GOST_YEAR])
    
    
    # Получаем исполнение проката
    prompt = f'Какое исполнение упомянуто в тексте: "{question}"' \
              '  Ответь одним словом.'
    
    qwe[OPTION] = ai(prompt, show=True)
    print(OPTION, qwe[OPTION])
    
    # Проверяем, что в ГОСТе упоминается это исполнение проката
    docs = rag('исполнение, исполнения', GOST_NUM, qwe[GOST_NUM], show=True)

    opt = qwe[OPTION]
    prompt = f'В этом тексте: {docs}, встречается исполнение "{opt}"? Ответь коротко.'
    prokat_option_in_gost = ai(prompt, show=True)
    if 'да' in prokat_option_in_gost.lower():
        qwe[OPTION_IN_DOC] = True
    else:
        qwe[OPTION_IN_DOC] = False
    
    # Получаем марку стали
    prompt = f'Какая марка стали упомянута в тексте: "{question}"' \
              '  Ответь одним словом.'
    qwe[STEEL] = ai(prompt, show=True)
    
    # Проверяем, что в ГОСТе упоминается эта марка стали
    docs = rag('сталь', GOST_NUM, qwe[GOST_NUM], show=True)
    opt = qwe[STEEL]
    prompt = f'В этом тексте: "{docs}", встречается марка стали "{opt}"? Ответь коротко.'
    steel_mark_in_gost = ai(prompt, show=True)
    if 'да' in steel_mark_in_gost.lower():
        qwe[STEEL_IN_DOC] = True
    else:
        qwe[STEEL_IN_DOC] = False
    
    # Получаем толщину проката
    prompt = f'Какая толщина упомянута в тексте: "{question}"' \
              '  Ответь одним словом.'
    qwe[THICKNESS] = ai(prompt, show=True)
    
    # Проверяем, что в ГОСТе упоминается эта толщина проката
    docs = rag('толщина', GOST_NUM, qwe[GOST_NUM], show=True)
    opt = qwe[THICKNESS]
    prompt = f'В этом тексте: "{docs}", встречается толщина проката "{opt}"? Ответь коротко.'
    res = ai(prompt, show=True)
    if 'да' in res.lower():
        qwe[THICKNESS_IN_DOC] = True
    else:
        qwe[THICKNESS_IN_DOC] = False
    
    # Получаем класс прочности проката
    prompt = f'Какой класс прочности упомянут в тексте: "{question}"' \
              '  Ответь одним словом.'
    qwe[SOLIDITY] = ai(prompt, show=True)
    
    # Проверяем, что в ГОСТе упоминается этот класс прочности
    docs = rag('класс прочности', GOST_NUM, qwe[GOST_NUM], show=True)
    opt = qwe[SOLIDITY]
    prompt = f'В этом тексте: "{docs}", встречается класс прочности "{opt}"? Ответь коротко.'
    res = ai(prompt, show=True)
    if 'да' in res.lower():
        qwe[SOLIDITY_IN_DOC] = True
    else:
        qwe[SOLIDITY_IN_DOC] = False

    # Получаем категорию проката
    prompt = f'Какая категория упомянута в тексте: "{question}"' \
              '  Ответь коротко.'
    res = ai(prompt, show=True)
    prompt = f'"Извлеки число из этого текста: "{res}"'
    qwe[CATEGORY] = ai(prompt, show=True)
    
    # Проверяем, что в ГОСТе упоминается эта категория проката
    docs = rag('категория', GOST_NUM, qwe[GOST_NUM], show=True)
    opt = qwe[CATEGORY]
    prompt = f'В этом тексте: "{docs}", встречается категория "{opt}"? Ответь коротко.'
    res = ai(prompt, show=True)
    if 'да' in res.lower():
        qwe[CATEGORY_IN_DOC] = True
    else:
        qwe[CATEGORY_IN_DOC] = False
    
    # Находим таблицы с нужной категорией
    opt = qwe[CATEGORY]
    docs = rag(f'категория {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается' \
             f' категория "{opt}"? Ответь коротко.'
    res = ai(prompt, show=True)
    
    prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко.'
    res = ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[CATEGORY_IN_TABLES] = res
    
    # Находим таблицы с нужной сталью
    opt = qwe[STEEL]
    docs = rag(f'сталь {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается сталь' \
             f' "{opt}"?' \
             ' Ответь коротко.Пример: Таблица 3, Таблица 7, Таблица 9'
    res = ai(prompt, show=True)
    
    #prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко.'
    #res = ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[STEEL_IN_TABLES] = res
    
    # Находим таблицы с нужным классом прочности
    opt = qwe[SOLIDITY]
    docs = rag(f'класс прочности {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается класс прочности' \
              f' "{opt}"?' \
              ' Ответь коротко. Пример: Таблица 3, Таблица 7, Таблица 9'
    res = ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[SOLIDITY_IN_TABLES] = res
    
    # Находим таблицы с нужным типом проката
    opt = qwe[PROKAT_TYPE]
    docs = rag(f'тип проката {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается тип проката' \
              f' "{opt}"?' \
              ' Ответь коротко. Пример: Таблица 3, Таблица 7, Таблица 9'
    res = ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[TYPE_IN_TABLES] = res
    
    # Находим таблицы с нужным исполнением
    opt = qwe[OPTION]
    docs = rag(f'исполнение проката {opt} таблица', GOST_NUM, qwe[GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается исполнение проката' \
              f' "{opt}"?' \
              ' Ответь коротко. Пример: Таблица 3, Таблица 7, Таблица 9'
    res = ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[OPTION_IN_TABLES] = res
    
    prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко. Пример: Таблица 3, Таблица 7, Таблица 9.'
    res = ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[OPTION_IN_TABLES] = res
    
    # Подготовка ответа на вопрос.
    tables = qwe[OPTION_IN_TABLES] 
    tables.extend(qwe[SOLIDITY_IN_TABLES])
    tables.extend(qwe[STEEL_IN_TABLES])
    tables.extend(qwe[TYPE_IN_TABLES])
    tables.extend(qwe[CATEGORY_IN_TABLES])
    tables = list(dict.fromkeys(tables))
    qwe[TABLES_OF_INTEREST] = sorted(tables)
    # where = {"$and": [{"category": "chroma"}, {"$or": [{"author": "john"}, {"author": "jack"}]}]}
    # where_cond = {"$and": [{"category": "chroma"}, {"author": "john"}]}
    #'gost_num': '19281', GOST_YEAR: '2014', 'type': 'table_body', 'table_number': '1'}
    # where_dict = {"$and": [{"gost_num": "19281"},{"$or": [{TABLE_NUMBER: "5"}, 
    #              {TABLE_NUMBER: "6"}, {TABLE_NUMBER: "11"},
    #              {TABLE_NUMBER: "12"}]}]}

    t_list = []
    for t in qwe[TABLES_OF_INTEREST]:
        t_list.append({TABLE_NUMBER: t})

    where_dict = {"$and": [{"gost_num": qwe[GOST_NUM]}, {"$or": t_list}]}
    print(where_dict)
    docs = rag_with_where(f'исполнение проката {opt} таблица', where_dict=where_dict, show=True)

    prompt_preambula = "Ты исследователь текста, который точно соблюдает инструкции.\n" 
    prompt = f'{prompt_preambula}Изучи таблицы: "{docs}" Перечисли перечень испытаний' \
             f' для {qwe[PROKAT_TYPE]} проката с исполнением' \
             f' {qwe[OPTION]} из стали {qwe["steel"]}' \
             f' класс прочности {qwe[SOLIDITY]} категория {qwe[CATEGORY]}' \
             f' толщина {qwe[THICKNESS]}?'

    res = ai(prompt, show=True)
    qwe[ANSWER] = res
    return qwe


# Запрос № 1
query_1 = 'Перечислите перечень испытаний для широкополосного проката (базовое' \
          ' исполнение), марка стали 09Г2С, толщина проката 25, класс прочности' \
          '  325, категория 12 для ГОСТ 19281-2014.'

# Ответ
answer_1 = 'Временное сопротивление, предел текучести, относительное удлинение,' \
           ' ударная вязкость -40 (KCU), ударная вязкость (KCU) мех. старение' \
           ' при комнатной температуре.'

#Запрос № 2
query_2 = 'Какие границы для испытания на временное сопротивление для широкополосного проката (базовое исполнение), марка стали 09Г2С, толщина проката 25, класс прочности 325, категория 12 для ГОСТ 19281-2014?'

#Ответ
answer_2 = 'Минимальная граница 450 Мпа.'

#Запрос № 3
query_3 = 'Какие границы для испытания на временное сопротивление для широкополосного проката, марка стали Ст3сп, толщина проката 20, категория 5 для ГОСТ 14637-89?'

#Ответ
answer_3 = 'Минимальная граница 370 Мпа. Максимальная граница 480 МПа.'

res = answering_machine(query_1)
print(res[ANSWER])
print(f"\nПравильный ответ:\n {answer_1}")
print('\n', res)
