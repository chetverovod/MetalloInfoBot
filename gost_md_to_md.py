#!/usr/bin/env python3

import os
import re
from os import listdir
from os.path import isfile, join
import config
import argparse
import re
from pathlib import Path
import ollama
import embeddings_ctrl as ec

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

CHUNK_CUT = '<--------------chunk_cut>---------------->'
CHUNK_SRC = 'chunk_src'
TABLE = "Таблица"
UNNAMED_TABLE = "Unnamed_table"
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
    t = t.split(f'<{tag}>')[1]
    return t


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


def build_txt(mode: str = '', page_separator: str = '') -> int:
    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    c = 0
    for path in files:
        if path.endswith(".md"):
            c += 1
    print(f"{c} gost md files found.")
    for path in files:
        relative_path = REF_DOCS_PATH + '/' + path
        filename = os.path.abspath(relative_path)
        extentions = filename.split(".")

        # Игнорируем не md-файлы.
        if extentions[-1] != "md":
            continue
        if "_chunked" in filename:
            continue
        with open(filename, "r", encoding="utf-8") as f:
            md = f.read()
        splitted_md = md.split('\n\n')

        # Первая строчка документа должна содержать его название.
        document_name = splitted_md[0]
        gost_num, gost_year = read_gost_number_year(document_name)

        table_name = UNNAMED_TABLE
        table_number = "undefined"
        bag = []
        for t in splitted_md:
            buf = ''
            buf = f'{buf}\n{CHUNK_CUT}'
            res = t.strip()
            pattern = r'\x20{2,}'
            res = re.sub(pattern, ' ', res)
            pattern = r'\| --- \|'
            res = re.sub(pattern, '|---|', res)
            pattern = r'\|\|'
            res = re.sub(pattern, '| |', res)

            chunk_type = 'paragraph'  
            if '|---|' in res:
                chunk_type = 'table_body'  
                t = wrap_by_tag(table_name, CHUNK_TABLE_NAME)
                t = f'{t}\n{res}'
                # Двойной перенос необходим чтобы тэг
                # не оказался внутри таблицы.
                t = wrap_by_tag(f'{t}\n', CHUNK_TABLE)
                buf = f'{buf}\n{t}'
                metas = {'gost_num': gost_num, 'gost_year': gost_year,
                         'type': chunk_type, 'table_number': table_number}
                ids = f'table_{table_number}_body'
            else:
                t_pos = res.find(TABLE)
                if t_pos == 0:
                    table_name = res
                    table_number = read_table_number(table_name)
                else:
                    table_name = UNNAMED_TABLE
                    table_number = "undefined"
                    buf = f'{buf}\n{res}\n'
                metas = {'gost_num': gost_num, 'gost_year': gost_year,
                         'type': chunk_type}
                ids = ''
            buf = add_tag(buf, CHUNK_META, f'{metas}')
            if len(ids) > 0:
                buf = add_tag(buf, CHUNK_IDS, f'{ids}')
            bag.append(buf)
        bulk = "\n".join(bag)
        print(bulk)

        chunks = bulk.split(CHUNK_CUT)
        clean_bag = []
        for i, chunk in enumerate(chunks):
            if len(chunk) < 3 * 80:
                ind = i + 1
                if ind < len(chunks):
                    if CHUNK_TABLE in chunks[i + 1]:
                        if CHUNK_TABLE not in chunks[i - 1]:
                            chunks[i - 1] = f'{chunks[i - 1]}\n{chunk}'
                            chunks[i] = ''
                    else:
                        chunks[i + 1] = f'{chunk}\n{chunks[i + 1]}'
                        chunks[i] = ''

        for i, chunk in enumerate(chunks):
            s = chunk.strip()
            if len(s) > 0:
                s = s.replace('\n\n', '\n')
                clean_bag.append(s)
        table_descriptions = []
        for i, buf in enumerate(clean_bag):
            if CHUNK_TABLE in buf:
                tn = read_tag(buf, CHUNK_TABLE_NAME)
                query = "This text contains table in markdown format." \
                        " Describe this table textually." \
                        f'Use Russian language. Table\n {buf}'
                         
                answer = ollama.generate(model=MAIN_MODEL, prompt=query,
                                           stream=False)
                res = answer['response']
                print('answer')
                desc = (
                        f'{BEGIN_TAG}\n'
                        f'<description_of_{CHUNK_NUMBER} {i+1}>\n'
                        f'<{CHUNK_SRC}>\n{document_name}'
                        f'\n</{CHUNK_SRC}>'
                        f'\n<{CHUNK_QUOTE}>'
                        f'\n{tn}'
                        f'\n{res}'
                        f'\n</{CHUNK_QUOTE}>\n')
                table_descriptions.append(desc)
                print(desc)

        for i, buf in enumerate(clean_bag):
            buf = (
                   f'{BEGIN_TAG}\n'
                   f'<{CHUNK_NUMBER} {i+1}>\n'
                   f'<{CHUNK_SRC}>\n{document_name}'
                   f'\n</{CHUNK_SRC}>'
                   f'\n<{CHUNK_QUOTE}>'
                   f'\n{buf}'
                   f'\n</{CHUNK_QUOTE}>\n')
            clean_bag[i] = buf
        clean_bag.extend(table_descriptions)

        for i, chunk in enumerate(clean_bag):
            buf = read_tag(chunk, CHUNK_QUOTE)            
            query = "This text is formatted in markdown format." \
                    " Describe this text by three or four tags." \
                    " If text contains a table include the table name to list of tags." \
                    " Your answer should contain only tags separated by comma." \
                    f" Use Russian language. Text:\n {buf}"
                         
            answer = ollama.generate(model=MAIN_MODEL, prompt=query,
                                     stream=False)
            res = answer['response']
            buf = (
                   f'{buf}'
                   f'\n<{CHUNK_TAGS}>'
                   f'\n{res}'
                   f'\n</{CHUNK_TAGS}>\n')
            print(buf)
            clean_bag[i] = buf
                  
        md_filename = filename.replace(".md", "_chunked.md")
        with open(md_filename, "w", encoding="utf-8") as f:
            print(f'Write: {md_filename}')
            f.write("\n".join(clean_bag))


if __name__ == "__main__":
    build_txt()
