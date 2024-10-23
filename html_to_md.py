#!/usr/bin/env python3

import os
import re
from os import listdir
from os.path import isfile, join
import config
import argparse
from collections import defaultdict
from bs4 import BeautifulSoup, NavigableString
import re
from pathlib import Path
from lxml_html_clean import Cleaner

# Load settings from configuration file.
cfg = config.Config('html_to_md.cfg')
REF_DOCS_PATH = cfg['reference_docs_path']
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

def replace_drop_words_by_stab(txt: str, drop_words_list: list[str], stab: str = STAB) -> str:
    for word in drop_words_list:
        if 'r"' in word:
            word = word.replace('r"', '"')
            word = word.replace('"', '')
            # Создаем регулярное выражение для поиска
            pattern = rf"{word}"
            # Заменяем все вхождения
            txt = re.sub(pattern, ' ', txt)
        else:
            txt = txt.replace(word, stab)
    return txt


def sanitize(dirty_html):
    cleaner = Cleaner(page_structure=True,
                      meta=True,
                      embedded=True,
                      links=True,
                      style=True,
                      processing_instructions=True,
                      inline_style=True,
                      scripts=True,
                      javascript=True,
                      comments=True,
                      frames=True,
                      forms=True,
                      annoying_tags=True,
                      remove_unknown_tags=True,
                      safe_attrs_only=True,
                      safe_attrs=frozenset(['src', 'color', 'href', 'name']),
                      remove_tags=('a', 'label', 'ul', 'i', 'li', 'footer',
                                   'noscript', 'span', 'font', 'div', 'svg',
                                   'img')
                      )

    return cleaner.clean_html(dirty_html)


def extract_table(table):
    postfix = '|'
    seporator = ''
    headers = []
    rows = []
    res = '' 
    for i, row in enumerate(table.find_all('tr')):
        if i == 0:
            headers = [el.text.strip() for el in row.find_all('th')]
        else:
            rows.append([el.text.strip() for el in row.find_all('td')])    
    res = f'{res}\n| {postfix.join(headers)} |\n'
    k = 0
    max = -1
    for row in rows:
        if len(row) > max:
            max = len(row)
    for i, row in enumerate(rows):
        if len(row) < max:
            m = max - len(row)
            for _ in range(m):
                rows[i].append(' ')
    for row in rows:
        res = f'{res}| {postfix.join(row)} |\n'
        if k == 0:
            for _ in range(len(row)):
                seporator += '|---'
            seporator = seporator + postfix
            res = f'{res}{seporator}\n'
            k += 1
    return res


def print_tables(tables):
    c = 1
    for t in tables:   
        print(f'## Table_{c}')
        c += 1
        print(t)

def build_txt(mode: str = '', page_separator: str = '') -> int:
    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    # Temporary jast two files parsing.
    #files = ['1200108697.html', '1200113779#7D20K3.html']
    #files = [
    #        'ГОСТ 14637-89 (ИСО 4995-78).html',
            #'ГОСТ 19281-2014_stroyinfo.html',
    #        ]
    c = 0
    for path in files:
        if path.endswith(".html"):
            c += 1
    print(f"{c} html files found.")
    for path in files:
        relative_path = REF_DOCS_PATH + '/' + path
        filename = os.path.abspath(relative_path)
        extentions = filename.split(".")

        # Игнорируем не html-файлы.
        if extentions[-1] != "html":
            continue
        with open(filename, "r", encoding="utf-8") as f:
            html = f.read()
        #print(html)    
        soup = BeautifulSoup(html, "lxml")
        tags = soup.findAll()
        tables = []
        c = 0

        for t in tags:
            if t.name == 'table':
                res = extract_table(t)
                tables.append(res)
        
        for table in soup.find_all("table"):
            table.extract()

        tags = soup.findAll()
        stop_flag = 0
        p_count = 0
        document_name = 'not_defined'
        CHUNK_CUT = '<--------------chunk_cut>---------------->'
        CHUNK_SRC = 'chunk_src'
        CHUNK_TABLE = 'chunk_table'
        CHUNK_QUOTE = 'chunk_quote'
        CHUNK_NUMBER = 'chunk_number'
        bag = []
        for t in tags:
            buf =''

            if stop_flag == 1:
                break
            if t.name == 'title':
                res = t.text.strip()
                document_name = res

            if t.name == 'h1':
                res = t.text.strip()
                buf = f'{buf}\n{CHUNK_CUT}'
                buf = f'{buf}\n## {res}\n'

            if t.name == 'h2':
                res = t.text.strip()
                buf = f'{buf}\n{CHUNK_CUT}'
                buf = f'{buf}\n### {res}\n'

            if t.name == 'h3':
                res = t.text.strip()
                buf = f'{buf}\n{CHUNK_CUT}'
                buf = f'{buf}\n### {res}\n'

            if t.name == 'p':
                res = t.text.strip()
                if "Таблица" in res:
                    for i, tbl in enumerate(tables):
                        if f'Таблица {i+1}' in res:
                            buf = f'{buf}\n{CHUNK_CUT}'
                            buf = f'{buf}\n<{CHUNK_TABLE}>'
                            buf = f'{buf}\n{res}'
                            buf = f'{buf}\n{tbl}'
                            # Двойной перенос необходим чтобы тэг
                            # не оказался внутри таблицы.
                            buf = f'{buf}\n\n</{CHUNK_TABLE}>\n'
                elif "Пожалуйста подождите" in res:
                    stop_flag = 1
                else:
                    if p_count == 0:
                        document_name = res
                        p_count = 1
                    else:
                        if len(res) > 0:
                            buf = f'{buf}{CHUNK_CUT}\n'
                            buf = f'{buf}\n{res}'
            bag.append(buf)

        bulk = "\n".join(bag)
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
        
        for i, buf in enumerate(clean_bag):
            buf = (
                   f'<{CHUNK_NUMBER} {i+1}>\n'
                   f'<{CHUNK_SRC}>\n{document_name}'
                   f'\n</{CHUNK_SRC}>'
                   f'\n<{CHUNK_QUOTE}>'
                   f'\n{buf}'
                   f'\n</{CHUNK_QUOTE}>\n')
            clean_bag[i] = buf
        md_filename = filename.replace(".html", ".md")
        with open(md_filename, "w", encoding="utf-8") as f:
            print(f'Write: {md_filename}')
            f.write("\n".join(clean_bag))


if __name__ == "__main__":
    build_txt()
