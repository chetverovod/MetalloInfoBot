from termcolor import colored
import model_io as mio
import ollama
import sys
import re

NUM_CTX = 8192 # 32768 #2048

#Запрос № 1
query_1 = 'Перечислите перечень испытаний для широкополосного проката (базовое' \
          ' исполнение), марка стали 09Г2С, толщина проката 25, класс прочности' \
          '  325, категория 12 для ГОСТ 19281-2014.'

#Ответ
answer_1 = 'Временное сопротивление, предел текучести, относительное удлинение,' \
           ' ударная вязкость -40 (KCU), ударная вязкость (KCU) мех. старение' \
           ' при комнатной температуре.'

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
#book.append(user_msg)
models_config_file = 'models.cfg'


def rag(context, gost_num: str = "", gost_year: str = ""):
    collection = mio.get_collection('metalloprokat')
    n_res = 5
    sz = 0
    limit = 200
    while sz < NUM_CTX and n_res < limit:
        sz = 0
        relevant_docs = collection.query(query_texts=(context),
                                         n_results=n_res,
                                         where={"gost_num": gost_num})
        rag_context = relevant_docs["documents"][0]

        for c in rag_context:
            sz += len(c)
        n_res += 1
    print(f"RAG volume = {sz}")
    print(f"RAG list len = {len(rag_context)}")
    return rag_context


def ai(prompt_txt: str) -> str:
    opt = {"temperature": 0, "num_ctx": NUM_CTX}  
    stream = ollama.generate(model='llama3.1', prompt=prompt_txt, options=opt)
    res = stream["response"]
    print(colored(f'>>> {res}\n', 'yellow'))
    return res


print(colored("Разбор запроса", "red"))
prompt = f"Изучи текст: {query_1} Какой " \
         " ГОСТ в нем упомянут? Выведи только обозначение ГОСТа."

res = ai(prompt)

prompt = f"Извлеки из текста обозначение ГОСТа. Вот из этого текста: {res}"
gost = ai(prompt)
gost_num = gost.split('-')[0]
print('Num:', gost_num)
gost_year = gost.split('-')[1]
print('Year:', gost_year)


full = False
if full:
   
    gost = 'ГОСТ 19281-2014'
    gost_num = '19281'
    gost_year = '2014'
    docs = rag('стандарт распространяется', gost_num, gost_year)
    print(colored(f'docs<{docs}>', 'green'))
    prompt = "Извлеки из текста информацию о том," \
             f" на какой горячекатанный прокат распространяется настоящий стандарт и перечисли виды этого проката." \
             f" Вот из этого текста: {docs}. Отвечай на русском языке."
    prokat_types = ai(prompt)

    prompt = f"Какой тип проката упомянут в тексте: {query_1} Ответь двумя словами."
    prokat_target = ai(prompt)

    docs = rag(f'испытан', gost_num, gost_year)
    print(colored(f'docs<{docs}>', 'green'))
    prompt = f"Каким испытания должен выдержать прокат {prokat_target}? Найди ответ в тексте: " \
             f"{docs}. Отвечай на русском языке."
    prokat_tests = ai(prompt)

    