from termcolor import colored
import model_io as mio
import ollama
import sys
import re
import config
import prokat as pr

DEFAULT_SETTINGS_FILE = 'models.cfg'
cfg = config.Config(DEFAULT_SETTINGS_FILE)
COLLECTION_NAME = cfg['collection_name']

TABLE_NUMBER = 'table_number'

# Dictionary key names.
#FORM = 'form'
#GOST_NUM = 'gost_num'
#GOST_YEAR = 'gost_year'
#OPTION = 'option' # исполнение
OPTION_IN_DOC = 'option_in_doc'
OPTION_IN_TABLES = 'option_in_tables'
#CATEGORY = 'category'
CATEGORY_IN_DOC = 'category_in_doc'
CATEGORY_IN_TABLES = 'category_in_tables'
STEEL_IN_DOC = 'steel_in_doc'
STEEL_IN_TABLES = 'steel_in_tables'
#THICKNESS = 'thickness'
THICKNESS_IN_DOC = 'thickness_in_doc'
TYPE_IN_TABLES = 'type_in_tables'
#SOLIDITY = 'solidity'
SOLIDITY_IN_DOC = 'solidity_in_doc'
SOLIDITY_IN_TABLES = 'solidity_in_tables'
TABLES_OF_INTEREST = 'tables_of_interest'
QUERY = 'query'
QUERY_DRY = 'query_dry' # Суть вопроса.
ANSWER = 'answer'

PROP_DICT = dict.fromkeys(pr.PROP_KEYS)
for key in PROP_DICT.keys():
    PROP_DICT[key] = '-'

pin = pr.ProkatInfo()




def rag_with_where(context, where_dict, show=False):
    collection = mio.get_collection(COLLECTION_NAME)
    n_res = 5
    sz = 0
    limit = 200
    while sz < pin.num_ctx and n_res < limit:
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
    while sz < pin.num_ctx and n_res < limit:
        sz = 0
        if len(meta_key) > 0:
            relevant_docs = collection.query(query_texts=(context),
                                             n_results=n_res,
                                             where={ meta_key: meta_value})
        else:
            relevant_docs = collection.query(query_texts=(context),
                                             n_results=n_res)

        
        rag_context = relevant_docs["documents"][0]

        for c in rag_context:
            sz += len(c)
        n_res += 1
    print(colored(f'rag_prompt<{context}>', 'green'))
    print(colored(f"RAG volume = {sz}", 'green'))
    print(colored(f"RAG list len = {len(rag_context)}", 'green'))
    if show:
        print(colored(f'rag docs<{rag_context}>', 'green'))
    return rag_context


def clean_up_tables_list(tables_string: str) -> list[str]:
    tables_string = tables_string.replace('[', '')
    tables_string = tables_string.replace(']', '')
    tables_string = tables_string.replace('Таблицы', '')
    tables_string = tables_string.replace('Таблица', '')
    tables_string = tables_string.split(',')
    tables_string = [s.strip() for s in tables_string]
    return tables_string


def answering_machine(question: str, show:bool = False) -> dict:
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

    qwe = PROP_DICT
    qwe[QUERY] = question

    # Получаем суть вопроса
    prompt = f'Ты внимательный аналитик текстов. Сделай вывод в чем состоит суть вопроса:\n"{question}".\n' \
              'Пример:\nТребуется составить список требований к прокату, который соответствует характеристикам:\n' \
              " - исполнение: базовое\n - класс прочности: 325\n - категория: 11\n"  
                
    qwe[QUERY_DRY] = pin.ai(prompt, show)

    # Получаем тип проката
    qwe[pr.PROKAT_TYPE] = pin.prokat_type(question)
    print(pr.PROKAT_TYPE, qwe[pr.PROKAT_TYPE])
    
    # Получаем форму проката
    qwe[pr.FORM] = pin.form(question)
    print(pr.FORM, qwe[pr.FORM])
    
    form = qwe[pr.FORM]
    rag_prompt = f'{form}'
    #docs = rag(rag_prompt, pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    docs = rag(rag_prompt, show=True)
    prompt = f'В каких таблицах из текста: "{docs}", встречается такая форма проката как "{form}"? Перечисли названия этих таблиц.'
    prokat_form_in_gost = pin.ai(prompt, show=True)
    print(prokat_form_in_gost)
    exit(0)

    # Получаем название ГОСТа
    qwe[pr.GOST_NUM], qwe[pr.GOST_YEAR] = pin.gost(question)
    print('GOST Num:', qwe[pr.GOST_NUM])
    print('GOST Year:', qwe[pr.GOST_YEAR])

    # Получаем исполнение проката
    qwe[pr.OPTION] = pin.option(question)
    print(pr.OPTION, qwe[pr.OPTION])

    # Проверяем, что в ГОСТе упоминается это исполнение проката
    docs = rag('исполнение, исполнения', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)

    opt = qwe[pr.OPTION]
    prompt = f'В этом тексте: {docs}, встречается исполнение "{opt}"? Ответь коротко.'
    prokat_option_in_gost = pin.ai(prompt, show=True)
    if 'да' in prokat_option_in_gost.lower():
        qwe[OPTION_IN_DOC] = True
    else:
        qwe[OPTION_IN_DOC] = False
    
    # Получаем марку стали
    qwe[pr.STEEL_MARK] = pin.steel_mark(question)
    
    # Проверяем, что в ГОСТе упоминается эта марка стали
    docs = rag('сталь', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    opt = qwe[pr.STEEL_MARK]
    prompt = f'В этом тексте: "{docs}", встречается марка стали "{opt}"? Ответь коротко.'
    steel_mark_in_gost = pin.ai(prompt, show=True)
    if 'да' in steel_mark_in_gost.lower():
        qwe[STEEL_IN_DOC] = True
    else:
        qwe[STEEL_IN_DOC] = False
    
    # Получаем толщину проката
    qwe[pr.THICKNESS] = pin.thickness(question)


    # Проверяем, что в ГОСТе упоминается эта толщина проката
    docs = rag('толщина', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    opt = qwe[pr.THICKNESS]
    prompt = f'В этом тексте: "{docs}", встречается толщина проката "{opt}"? Ответь коротко.'
    res = pin.ai(prompt, show=True)
    if 'да' in res.lower():
        qwe[THICKNESS_IN_DOC] = True
    else:
        qwe[THICKNESS_IN_DOC] = False
    
    # Получаем класс прочности проката
    qwe[pr.SOLIDITY] = pin.solidity_class(question)
    
    # Проверяем, что в ГОСТе упоминается этот класс прочности
    docs = rag('класс прочности', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    opt = qwe[pr.SOLIDITY]
    prompt = f'В этом тексте: "{docs}", встречается класс прочности "{opt}"? Ответь коротко.'
    res = pin.ai(prompt, show=True)
    if 'да' in res.lower():
        qwe[SOLIDITY_IN_DOC] = True
    else:
        qwe[SOLIDITY_IN_DOC] = False

    # Получаем категорию проката
    qwe[pr.CATEGORY] = pin.category(question)
    print(qwe)
    # Проверяем, что в ГОСТе упоминается эта категория проката
    docs = rag('категория', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    opt = qwe[pr.CATEGORY]
    prompt = f'В этом тексте: "{docs}", встречается категория "{opt}"? Ответь коротко.'
    res = pin.ai(prompt, show=True)
    if 'да' in res.lower():
        qwe[CATEGORY_IN_DOC] = True
    else:
        qwe[CATEGORY_IN_DOC] = False
    
    # Находим таблицы с нужной категорией
    opt = qwe[pr.CATEGORY]
    docs = rag(f'категория {opt} таблица', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается' \
             f' категория "{opt}"? Ответь коротко.'
    res = pin.ai(prompt, show=True)
    
    prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко.'
    res = pin.ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[CATEGORY_IN_TABLES] = res
    
    # Находим таблицы с нужной сталью
    opt = qwe[pr.STEEL_MARK]
    docs = rag(f'сталь {opt} таблица', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается сталь' \
             f' "{opt}"?' \
             ' Ответь коротко.Пример: Таблица 3, Таблица 7, Таблица 9'
    res = pin.ai(prompt, show=True)
    
    #prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко.'
    #res = pin.ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[STEEL_IN_TABLES] = res
    
    # Находим таблицы с нужным классом прочности
    opt = qwe[pr.SOLIDITY]
    docs = rag(f'класс прочности {opt} таблица', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается класс прочности' \
              f' "{opt}"?' \
              ' Ответь коротко. Пример: Таблица 3, Таблица 7, Таблица 9'
    res = pin.ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[SOLIDITY_IN_TABLES] = res
    
    # Находим таблицы с нужным типом проката  или  формой
    opt = qwe[pr.PROKAT_TYPE]
    docs = rag(f'тип проката {opt} или форма проката {qwe[pr.FORM]} таблица', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается тип проката' \
              f' "{opt}" или форма проката {qwe[pr.FORM]}?' \
              ' Ответь коротко. Пример: Таблица 3, Таблица 7, Таблица 9'
    res = pin.ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[TYPE_IN_TABLES] = res
    
    # Находим таблицы с нужным исполнением
    opt = qwe[pr.OPTION]
    docs = rag(f'исполнение проката {opt} таблица', pr.GOST_NUM, qwe[pr.GOST_NUM], show=True)
    prompt = f'В этом тексте: "{docs}", найди в каких таблицах встречается исполнение проката' \
              f' "{opt}"?' \
              ' Ответь коротко. Пример: Таблица 3, Таблица 7, Таблица 9'
    res = pin.ai(prompt, show=True)
    res = clean_up_tables_list(res)
    qwe[OPTION_IN_TABLES] = res
    
    prompt = f'Извлеки названия таблиц из этого текста: "{res}". Ответь коротко. Пример: Таблица 3, Таблица 7, Таблица 9.'
    res = pin.ai(prompt, show=True)
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

    t_list = []
    for t in qwe[TABLES_OF_INTEREST]:
        t_list.append({TABLE_NUMBER: t})

    where_dict = {"$and": [{"gost_num": qwe[pr.GOST_NUM]}, {"$or": t_list}]}
    print(where_dict)
    docs = rag_with_where(f'исполнение проката {opt} таблица', where_dict=where_dict, show=True)

    ct = pin.build_characteristic_table()
    print(f'build_characteristic_table: {ct}')
    prompt_preambula = "Ты исследователь текста, который точно соблюдает инструкции.\n" 
    prompt = f'{prompt_preambula} Изучи таблицы:\n"{docs}"\n Для проката со следующими характеристиками:\n' \
             f'{ct} Ответь на вопрос: {qwe[QUERY]}'
    # f'{ct} Ответь на вопрос: {qwe[QUERY_DRY]}'
   
    res = pin.ai(prompt, show=True)
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

# Запрос № 2
query_2 = 'Какие границы для испытания на временное сопротивление для' \
          ' широкополосного проката (базовое исполнение), марка стали 09Г2С,' \
          ' толщина проката 25, класс прочности 325, категория 12 для ГОСТ 19281-2014?'

# Ответ
answer_2 = 'Минимальная граница 450 Мпа.'

# Запрос № 3
query_3 = 'Какие границы для испытания на временное сопротивление для' \
          ' широкополосного проката, марка стали Ст3сп, толщина проката' \
          ' 20, категория 5 для ГОСТ 14637-89?'

# Ответ
answer_3 = 'Минимальная граница 370 Мпа. Максимальная граница 480 МПа.'
res = {}

filename = 'knowledge/gost_19281_2014_text.txt'
with open(filename, "r", encoding="utf-8") as f:
    docs = f.read()
#prompt = f'В этом тексте: {docs}, найди ответ на вопрос: "{query_1}"?'
prompt = f"""Ты исследователь текстов, который абсолютно точно соблюдает инструкции.
Имеется текст нормативно-технического документа:
{docs}
Этот текст необходимо разбить на обособленные по смыслу фрагменты для записи в базу данных.
Фрагменты должны быть как можно меньшего размера, но при этом не должен теряться их смысл. 
В выводе напечатай этот текст, разделенный на фрагменты.
Для разделения фрагменты используй строку '----------------------------------------------------------------------------------------------------'.
В выводе должен быть только текст без комментариев. Пример ответа:
----------------------------------------------------------------------------------------------------
3.23 высокий отпуск: Технологический процесс нагрева проката ниже температуры , выдержки и охлаждения его с заданной скоростью или на спокойном воздухе.
----------------------------------------------------------------------------------------------------
3.24 механическое старение: Процесс искусственного старения в соответствии с ГОСТ 7268.
----------------------------------------------------------------------------------------------------
"""

pin.num_ctx = 20000
res = pin.ai(prompt, show=True)
with open(filename + '_ch', "w", encoding="utf-8") as f:
    docs = res.write()

exit(0)

filename = 'knowledge/gost_19281_2014_text.txt'
with open(filename, "r", encoding="utf-8") as f:
    docs = f.read()
prompt = f'В этом тексте: {docs}, найди ответ на вопрос: "{query_1}"?'
pin.num_ctx = 20000
res = pin.ai(prompt, show=True)
exit(0)

res[1] = answering_machine(query_1, show=True)
print(res[1][ANSWER])
print(f"\nПравильный ответ:\n {answer_1}")
"""

res[2] = answering_machine(query_2)
print(res[2][ANSWER])
print(f"\nПравильный ответ:\n {answer_2}")

res[3] = answering_machine(query_3)
print(res[3][ANSWER])
print(f"\nПравильный ответ:\n {answer_3}")
res = pin.prokat_type(query_1)
res = pin.prokat_type(query_2)
res = pin.prokat_type(query_3)

res = pin.form(query_1)
res = pin.form(query_2)
res = pin.form(query_3)

"""

