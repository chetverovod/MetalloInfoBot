from termcolor import colored
import ollama


NUM_CTX = 8192 # 32768 #2048

# Dictionary key names.
PROKAT_TYPE = 'prokat_type'
FORM = 'form'
GOST_NUM = 'gost_num'
GOST_YEAR = 'gost_year'
OPTION = 'option' # исполнение
OPTION_IN_DOC = 'option_in_doc'
OPTION_IN_TABLES = 'option_in_tables'
CATEGORY = 'category'
CATEGORY_IN_DOC = 'category_in_doc'
CATEGORY_IN_TABLES = 'category_in_tables'
STEEL_CLASS = 'steel_class'
STEEL_MARK = 'steel_mark'
STEEL_IN_DOC = 'steel_in_doc'
STEEL_IN_TABLES = 'steel_in_tables'
THICKNESS = 'thickness'
THICKNESS_IN_DOC = 'thickness_in_doc'
TYPE_IN_TABLES = 'type_in_tables'
SOLIDITY = 'solidity'
SOLIDITY_IN_DOC = 'solidity_in_doc'
SOLIDITY_IN_TABLES = 'solidity_in_tables'
TABLES_OF_INTEREST = 'tables_of_interest'
QUERY = 'query'
QUERY_DRY = 'query_dry' # Суть вопроса.
ANSWER = 'answer'


PROP_KEYS = [
             PROKAT_TYPE, FORM, GOST_NUM,
             GOST_YEAR, OPTION, OPTION_IN_DOC,
             OPTION_IN_TABLES, CATEGORY,
             CATEGORY_IN_DOC, CATEGORY_IN_TABLES,
             STEEL_CLASS, STEEL_MARK, STEEL_IN_DOC,
             STEEL_IN_TABLES, THICKNESS,
             THICKNESS_IN_DOC, TYPE_IN_TABLES,
             SOLIDITY, SOLIDITY_IN_DOC,
             SOLIDITY_IN_TABLES, TABLES_OF_INTEREST,
             QUERY, QUERY_DRY, ANSWER
            ]

PROP_DICT = dict.fromkeys(PROP_KEYS)
for key in PROP_DICT.keys():
    PROP_DICT[key] = '-'
    
#4.1 Прокат изготовляют:
# по видам:
prokat_types = [
"толстолистовой", "широкополосный универсальный",
"сортовой", "фасонный", "гнутые профили"
]
# по классам качества стали:
steel_classes = [
'нелегированная качественная', 'легированная']

# по классам прочности:
solidity_classes = [
 # с обозначением по настоящему стандарту;
265, 295, 315, 325, 345, 355, 375, 390, 440, 460, 500, 550, 600, 620, 650, 700]
# S235; S275; S355 - с обозначением по стандарту \[[2](#i596364 "Библиография [2]")\], где буква S означает - «конструкционная сталь», цифра - минимальное значение предела текучести для проката диаметром до 16 мм включительно;

# по требованиям к химическому составу стали:
# - с химическим составом, ограниченным сверху, с целью исключения превышения
#   прочностных характеристик проката, предусмотренных классом прочности;

# - с химическим составом, установленным для марки стали (композиции), гарантирующим
#  обеспечение комплекса свойств для класса прочности;

#по категориям поставки в зависимости от нормируемых
# характеристик механических свойств при испытании на ударный изгиб - от 1 до 20.    
categories = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

# По форме, размерам и предельным отклонениям по форме и размерам продукция должна соответствовать требованиям:
# - прокат сортовой:
forms = [ 'сортовой', 'фасонный']
sorts = [
         "круглый в прутках и мотках", "квадратный в прутках и мотках",
         "шестигранный в прутках и мотках", "полосовой", "толстолистовой",
         "широкополосный универсальный"]

# - прокат фасонный:
fasons = [
          "уголок равнополочный", "уголок неравнополочный", "швеллеры",
          "двутавры", "двутавры с параллельными гранями полок",
          "профили специального назначения", "профили гнутые"
         ]


class ProkatInfo:
    def __init__(self):
        self.info = dict.fromkeys(PROP_KEYS)
        for key in self.info.keys():
            self.info[key] = '-'
        self.num_ctx = NUM_CTX  
    def ai(self, prompt_txt: str, show=False) -> str:
        if show:
            print(colored(f"promt: {prompt_txt}\n", 'light_yellow'))
        opt = {"temperature": 0, "num_ctx": self.num_ctx}
        stream = ollama.generate(model='llama3.1', prompt=prompt_txt,
                                 options=opt)
        res = stream["response"].removesuffix('.')
        print(colored(f'>>> {res}\n', 'yellow'))
        return res

    def prokat_type(self, question: str) -> dict:
        preambula = f'Существующие типы металлического проката перечислены через запятую: {prokat_types}.\n'  
        prompt = f'{preambula} Какой тип проката имеется в виду в этом тексте:\n "{question}"' \
                 ' Ответь коротко, одним из перечисленных выше типов.'
        res = self.ai(prompt)
        self.info[PROKAT_TYPE] = res
        return res

    def steel_class(self, question: str) -> dict:
        preambula = f'Существующие классы стали проката перечислены через запятую: {steel_classes}.\n'  
        prompt = f'{preambula} Какой класс стали имеется в виду в этом тексте:\n "{question}"' \
                 '  Ответь коротко, одним из перечисленных выше типов.'
        res = self.ai(prompt)
        self.info[STEEL_CLASS] = res
        return res

    def steel_mark(self, question: str) -> dict:
        preambula = f'Примеры обозначения марок стали перечислены через запятую: {steel_classes}.\n'  
        prompt = f'{preambula} Какая марка стали имеется в виду в этом тексте:\n "{question}"' \
                 '  Ответь коротко.'
        res = self.ai(prompt)
        self.info[PROKAT_TYPE] = res
        return res

    def form(self, question: str) -> dict:
        p_type = self.prokat_type(question)
        preambula = f'Существующие две формы металлического проката перечислены через запятую: {forms}.' \
                    f' К форме {forms[0]} относят прокаты из списка {sorts}.\n' \
                    f' К форме {forms[1]} относят прокаты из списка {fasons}.\n' 

        prompt = f'{preambula} Какая форма проката имеется в виду в этом тексте:\n "{p_type}"' \
                 ' Ответь коротко, одним из перечисленных выше типов.'
        res = self.ai(prompt)
        self.info[FORM] = res
        return res
