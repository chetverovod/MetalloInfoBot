import json


class Chain_of_thoughts():
    def __init__(self, question: str = None):
        self.doc_num = False
        if question is not None:
            self.start(question)

    def search_doc_num(self, question: str) -> None:
        """
        Ищем в запросе номер НТД
        """
        prompt = f"""Ты исследователь текстов, который абсолютно точно соблюдает инструкции.
Представлен следующий запрос о поиске информации в базе данных:
{question}
Определи, имеется ли в тексте запроса идентификатор нормативно-технического документа (НТД).
Идентификатор НТД состоит из нескольких частей. Сначала идет название НТД (например, 'ГОСТ' или 'ТУ').
После этого идет номер НТД (например, '12345'). В конце идет год выпуска НТД (например, '2010' или '85').
Примеры обозначения НТД в тексте: ГОСТ 123456-2015, ГОСТ 222222 2022, ТУ 543-86.
В ответе выведи номер документа без дополнительных комментариев. 
Если номера нет, напиши просто 'нет': 
Примеры ответов:
ГОСТ 123456-2015
ГОСТ 222222-2022
ТУ 543-1986
нет"""
        # TODO Здесь нужно переделать вывод
        answer = self.llm_request(prompt)
        print("Answer:", answer)
        if answer != "нет":
            try:
                self.doc_num = answer.split(' ')
                self.doc_num = self.doc_num[1].split('-')[0]
            except:
                print("Ошибка парсинга номера НТД")

    def start(self, question: str) -> str:
        """
        Определяем, в каком разделе искать информацию по данному запросу
        """
        self.search_doc_num(question)    # Определение номера ГОСТ
        prompt = f"""Ты исследователь текстов, который абсолютно точно соблюдает инструкции.
Представлен следующий запрос о поиске информации в базе данных:
{question}
Часть информации в базе данных содержится в текстовом виде, часть в таблицах, а часть в графичесом виде - схемах или рисунках.
Если в запросе указано много различных числовых параметров, значит ответ нужно искать в таблице.
Если требуется найти определение термина, значит ответ необходимо искать в тексте.
Где необходимо искать ответ для данного запроса: в текстах, таблицах или схемах/рисунках?
В качестве ответа просто напиши 'текст' или 'таблица' или 'схема/рисунок'. Примеры ответа:
Текст
Таблица
Схема/рисунок"""
        answer = self.llm_request(prompt)
        print("Start Answer:", answer)
        if "текст" in answer.lower():
            res = self.find_by_text(question=question)
        elif "таблица" in answer.lower():
            res = self.find_by_tables_meta(question)
        elif "схема/рисунок" in answer.lower():
            pass
        else:
            pass
        return res

    def find_by_text(self, question: str) -> dict:
        """
        Ищем ответ в текстовых блоках
        """
        filter_list = [{"gost_num": str(self.doc_num)}, {"type": "paragraph"}]
        db_answer = self.query_to_db(question, filter_list)
        db_answer = '\n'.join(db_answer['documents'][0])
        prompt = f"""Ты исследователь текстов, который абсолютно точно соблюдает инструкции.
Представлен следующий запрос о поиске информации в базе данных:
{question}
Получена информация из базы данных.
{db_answer}
Проанализируй её и ответь на поставленный вопрос."""
        answer = self.llm_request(prompt)
        print(answer)

    def find_by_tables_meta(self, question: str) -> dict:
        """
        Определяем параметры для выбора нужной таблицы
        """

        print("find_by_tables_meta Answer")
        if self.doc_num:
            filter_list = [{"gost_num": str(self.doc_num)}, {"type": "table_meta"}]
        else:
            filter_list = [{"type": "table_meta"}]
        print(filter_list)
        db_answer = self.query_to_db(question, filter_list, n_results=100)
        tables_for_analyse = ''
        for table_meta in db_answer['documents'][0]:
            table_meta = table_meta[14:]
            table_meta = table_meta.split('\n')
            table_meta = json.loads(table_meta[0].replace("'", '"'))
            table_num = table_meta['Название таблицы'].split()[1]
            prompt = f"""Ты исследователь текстов, который абсолютно точно соблюдает инструкции.
Представлены метаданные таблицы:
Название таблицы: {table_meta['Название таблицы']}, колонки таблицы: {list(table_meta.keys())}
Определи по этим метаданным, может ли в ней содержаться ответ на вопрос:
{question}
В ответе использовать только слова 'Да' или 'Нет', никаких дополнительных комментариев приводить не нужно.
Примеры ответа:
нет
да"""
            answer = self.llm_request(prompt)
            if answer.lower() == 'да':
                filter_list = [
                    {"gost_num": str(self.doc_num)},
                    {'table_number': table_num.upper()},
                    {"type": "table_body"}
                ]
                table_body = self.query_to_db(question, filter_list, n_results=1)
                tables_for_analyse += table_body['documents'][0][0] + '\n'
        print("tables_for_analys:", tables_for_analyse)
        prompt = f"""Ты исследователь текстов, который абсолютно точно соблюдает инструкции.
Представлены таблицы:
{tables_for_analyse}
Проанализируй эти таблицы, сопоставь указанные в них данные и ответь на вопрос:
{question}
Ответ должен быть кратким. Повторять вопрос в ответе не нужно. 
Примеры ответов:
Минимальная граница: 300 Н/мм;
Содержание серы: 0.025.
Диаметр оправки: 0.5
Рабочая нагрузка: 300 КПа."""
        res = self.llm_request(prompt)
        print(res)
        return res
