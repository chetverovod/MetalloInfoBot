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
        gost_num, gost_year = cc.read_gost_number_year(document_name)

        table_name = cc.UNNAMED_TABLE
        table_number = "undefined"
        bag = []
        for t in splitted_md:
            buf = ''
            buf = f'{buf}\n{cc.CHUNK_CUT}'
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
                t = cc.wrap_by_tag(table_name, cc.CHUNK_TABLE_NAME)
                t = f'{t}\n{res}'
                # Двойной перенос необходим чтобы тэг
                # не оказался внутри таблицы.
                t = cc.wrap_by_tag(f'{t}\n', cc.CHUNK_TABLE)
                buf = f'{buf}\n{t}'
                metas = {'gost_num': gost_num, 'gost_year': gost_year,
                         'type': chunk_type, 'table_number': table_number}
                ids = f'table_{table_number}_body'
            else:
                t_pos = res.find(cc.TABLE)
                if t_pos == 0:
                    table_name = res
                    table_number = cc.read_table_number(table_name)
                else:
                    table_name = cc.UNNAMED_TABLE
                    table_number = "undefined"
                    buf = f'{buf}\n{res}\n'
                metas = {'gost_num': gost_num, 'gost_year': gost_year,
                         'type': chunk_type}
                ids = ''
            buf = cc.add_tag(buf, cc.CHUNK_META, f'{metas}')
            if len(ids) > 0:
                buf = cc.add_tag(buf, cc.CHUNK_IDS, f'{ids}')
            bag.append(buf)
        bulk = "\n".join(bag)
        print(bulk)

        # Подклеиваем короткие чанки к их соседям.
        chunks = bulk.split(cc.CHUNK_CUT)
        for i, chunk in enumerate(chunks):
            if len(chunk) < 3 * 80:
                ind = i + 1
                if ind < len(chunks):
                    if cc.CHUNK_TABLE in chunks[i + 1]:
                        if cc.CHUNK_TABLE not in chunks[i - 1]:
                            chunks[i - 1] = f'{chunks[i - 1]}\n{cc.read_tag(chunk, cc.CHUNK_QUOTE)}'
                            chunks[i] = ''
                    else:
                        chunks[i + 1] = f'{chunk}\n{cc.read_tag(chunks[i + 1], cc.CHUNK_QUOTE)}'
                        chunks[i] = ''

        clean_bag = []
        for i, chunk in enumerate(chunks):
            s = chunk.strip()
            if len(s) > 0:
                s = s.replace('\n\n', '\n')
                clean_bag.append(s)

        for i, buf in enumerate(clean_bag):
            buf = (
                   f'{cc.BEGIN_TAG}\n'
                   f'<{cc.CHUNK_NUMBER} {i+1}>\n'
                   f'<{cc.CHUNK_SRC}>\n{document_name}'
                   f'\n</{cc.CHUNK_SRC}>'
                   f'\n<{cc.CHUNK_QUOTE}>'
                   f'\n{buf}'
                   f'\n</{cc.CHUNK_QUOTE}>\n')
            clean_bag[i] = buf

        table_descriptions = []
        for i, buf in enumerate(clean_bag):
            if cc.CHUNK_TABLE in buf:
                tn = cc.read_tag(buf, cc.CHUNK_TABLE_NAME)
                query = "This text contains table in markdown format." \
                        " Describe this table textually." \
                        f'Use Russian language. Table\n {buf}'

                answer = ollama.generate(model=cc.MAIN_MODEL, prompt=query,
                                         stream=False)
                res = answer['response']
                print('answer')
                desc = (
                        f'{cc.BEGIN_TAG}\n'
                        f'<description_of_{cc.CHUNK_NUMBER} {i+1}>\n'
                        f'<{cc.CHUNK_SRC}>\n{document_name}'
                        f'\n</{cc.CHUNK_SRC}>'
                        f'\n<{cc.CHUNK_QUOTE}>'
                        f'\n{tn}'
                        f'\n{res}'
                        f'\n</{cc.CHUNK_QUOTE}>\n')
                table_descriptions.append(desc)
                print(desc)
        clean_bag.extend(table_descriptions)

        # Добавляем слова-теги.
        for i, chunk in enumerate(clean_bag):
            buf = cc.read_tag(chunk, cc.CHUNK_QUOTE)
            query = "This text is formatted in markdown format." \
                    " Describe this text by three or four keywords." \
                    " If text contains a table include the table name to list of keywords." \
                    " Your answer should contain only keywords separated by comma." \
                    f" Use Russian language. Text:\n {buf}"

            answer = ollama.generate(model=cc.MAIN_MODEL, prompt=query,
                                     stream=False)
            res = answer['response']
            res = res.replace('Теги:', '')
            res = res.replace('Метки:', '')
            res = res.replace('Мета-метки:', '')
            res = res.replace('Ключевые слова:', '') 
            chunk = (
                   f'{chunk}'
                   f'\n<{cc.CHUNK_TAGS}>'
                   f'\n{res}'
                   f'\n</{cc.CHUNK_TAGS}>\n')
            print(chunk)
            clean_bag[i] = chunk
 
        md_filename = filename.replace(".md", "_chunked.md")
        with open(md_filename, "w", encoding="utf-8") as f:
            print(f'Write: {md_filename}')
            f.write("\n".join(clean_bag))


if __name__ == "__main__":
    build_txt()
