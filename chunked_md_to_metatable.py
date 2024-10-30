#!/usr/bin/env python3

import os
import re
from os import listdir
from os.path import isfile, join
import config
import chunk_ctrl as cc
import argparse
import re
from pathlib import Path
import ollama

# Load settings from configuration file.
cfg = config.Config('html_to_md.cfg')
p = cfg['reference_docs_path'].split('/')
REF_DOCS_PATH = f'{p[0]}/{p[1]}'
TITLE_TAG = cfg['title_tag']
SOURCE_TAG = cfg['source_tag']
QUOTE_TAG = cfg['quote_tag']
CHUNKING = cfg['chunking']
DROP_WORDS = cfg['drop_words']
PARAGRAPH_TAG = 'paragraph'
PARAGRAPH_BORDER = '----paragraph_border----'
PAGE_HEADER_END = 'page_header_end'
PAGE_NUMBER_TAG = 'page_number'  # page number
END_OF_PAGE_TAG = 'end_of_page'
DOCUMENT = 'document'
PAGE_SEPARATOR = '<------------------page_separator-------------------->'
SENTENCE_SEPARATOR = '. ' 
STAB = 'blabla'


def extract_first_table_info(text):
    # Регулярное выражение для поиска первой строки, начинающейся с 'Таблица',
    # за которой следует пробел, идентификатор таблицы (число или буква + точка + число),
    # еще один пробел и имя таблицы
    #pattern = r'^Таблица\s+((?:\d+)|(?:[a-zA-Z]\.\d+))\s+(.*)$'
    pattern = r'^Таблица\s+((?:\d+)|(?:[а-яА-Я]\.\d+))\s+(.*)$' 
    # Находим первое совпадение в тексте
    match = re.search(pattern, text, flags=re.MULTILINE)

    if match:
        table_id = match.group(1)
        table_name = match.group(2)
        return table_id, table_name
    else:
        return None, None  # Если совпадений нет, возвращаем None


def build_metatables(use_ai: bool = False) -> int:
    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    c = 0
    for path in files:
        if path.endswith("chunked.md"):
            c += 1
    print(f"{c} chunked md files found.")
    for path in files:
        relative_path = REF_DOCS_PATH + '/' + path
        filename = os.path.abspath(relative_path)
        extentions = filename.split(".")

        # Игнорируем не md-файлы.
        if extentions[-1] != "md":
            continue
        if "_chunked" not in filename:
            continue
        with open(filename, "r", encoding="utf-8") as f:
            md = f.read()
        chunks = md.split(cc.BEGIN_TAG) 
        stop = 0
        for chunk in chunks:
            if cc.is_tag_in_text(chunk, cc.CHUNK_TABLE):
                chunk = cc.remove_tag(chunk, cc.CHUNK_META)
                chunk = cc.remove_tag(chunk, cc.CHUNK_TAGS)
                chunk = cc.remove_tag(chunk, cc.CHUNK_IDS)
                chunk = cc.remove_tag(chunk, cc.CHUNK_SRC)
                chunk = cc.remove_tag(chunk, cc.CHUNK_TABLE_NAME)
                chunk = cc.remove_tag(chunk, cc.CHUNK_NUMBER)
                chunk = cc.unwrap_from_tag(chunk, cc.CHUNK_QUOTE)
                chunk = cc.unwrap_from_tag(chunk, cc.CHUNK_TABLE)
                chunk = re.sub(r'\n{2,}', '\n', chunk)
                print('------------------------------------')
                if use_ai is True:
                    query = f"""Это:\n {chunk} \n - описание таблицы в формате "markdown".
                     В самой верхней строке описания находится название таблицы.
                     Создай из этой таблицы питоновский словарь,
                     в каждой  паре ключ-значение,
                     ключ это название колонки исходной таблицы, 
                     а значение это список уникальных значений в этой
                     колонке исходной таблицы.\n" Первый элемент словаря
                     должен иметь ключ "Название таблицы", а значение должно
                     хранить название таблицы и её номер.
                    Пример:\n
                    {{\n
                    "Название таблицы": "таблица 1 - химический состав стали по анализу ковшевой пробы",\n
                    "Класс прочности": ["265, 295", "315", "325", "345", "355", "375", "390", "440"],\n
                    "Массовая доля элементов, %, не более": ["С", "Si", "Мn", "Р", "S", "Сr", "Ni", "Сu", "V", "N"]\n
                    }}
                    """    
                    opt = {"temperature": 0.}
                    metatable = ollama.generate(model=cc.MAIN_MODEL, prompt=query, options=opt)['response']
                    print(metatable)
                else:
                    print(chunk)
                stop += 1
                if stop > 3:
                    exit(0)    


if __name__ == "__main__":
    build_metatables(use_ai=True)
    #build_metatables()

