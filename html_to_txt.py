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
import pandas

# Load settings from configuration file.
cfg = config.Config('html_to_txt.cfg')
COLLECTION_NAME = cfg['collection_name']
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

def find_max_integer_key(dictionary):
    max_value = max(dictionary.values())
    for key, value in dictionary.items():
        if value == max_value:
            return key


def count_phrase_frequency(text, page_counter, print_top_n=-1):
    #print_top_n = 30
    t = re.sub(r'\n+', '\n', text)
    t = re.sub(r'_{1,}', ' ', t)
    t = re.sub(r'\…{1,}', ' ', t)
    t = re.sub(r'\.{2,}', '. ', t)
    t = re.sub(r'\s+', ' ', t)

    sentences = t.split(SENTENCE_SEPARATOR)
    #print('page_counter:', page_counter)
    #print('len(sentences):', len(sentences))
    #print('\n\n'.join(sentences))
    phrase_counts = defaultdict(lambda: 0)

    for sentence in sentences:
        words = sentence.split()
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                phrase = ' '.join(words[i:j])
                phrase_counts[phrase] += 1

    ph = {}
    for phrase, count in phrase_counts.items():
        #if (count > (page_counter - 7)) and (count < (page_counter + 5)):
        if (count > (page_counter/2)) and (count < (page_counter + 5)):
        #if (count > 0):
            words = phrase.split(' ')
            if words[0][0].isupper():
                upper = 1.5
            else:
                upper = 1
            score = len(words) * count * upper
            ph[phrase] = score
    if len(ph) > 0:
        doc_name = find_max_integer_key(ph)
        if print_top_n > 0:
            for phrase, count in sorted(ph.items(), key=lambda item: item[1],
                                        reverse=True)[:print_top_n]:
                print(f'score: {count}  phrase: "{phrase}"')
    else:
        doc_name = 'not found'
    return doc_name

def scan_tag_text(tag):
    res = ''
    name = tag.name
    s = tag.string
    if s is None:
        s = '    ' 
    if name == 'head':
        res = f'\n{s}'
    if name == 'title': 
        res = f'\n{s}'
    if name == 'table':
        res = f'\n{s}'
    if name == 'tbody':
        res = f'----------------------------------------------------------------------------------\n|'
    if name == 'tr':
        res = f'\n--------------------------------------------------------------------------------\n|'
    if name == 'th':
        res = f'| '
    if name == 'td':
        res = f'| '
    if name == 'p':
        res = f'{s}'
    return res

def build_flat_txt_doc(filename: str,
                       page_separator: str = '\n\n') -> (str, int):
    if not filename.endswith(".html"):
        return "", -1
    page_counter = 0
    complete_text = ''

    # Получаем содержимое страницы
    with open(filename) as fp:
        soup = BeautifulSoup(fp, 'html.parser')
    """
    for tag in soup.find_all(): 
        s = scan_tag_text(tag)
        complete_text = f'{complete_text}{s}'
    txt = complete_text 
    """
    #par =  soup.find("p", {'id': "P0002"})
    #print(par)
    """
        for element in list(par.descendants):
            print(element.name)
            if type(element) is NavigableString:
                markup = element.string.replace("Ж", " Х ")
                element.string.replace_with(BeautifulSoup(markup, "html.parser"))
    """
    tags = soup.findAll()
    stop_list = [ 'html','body', 'head', 'a','form', 'div', 'meta','footer','input', 'button', 'script',
                 'noscript', 'link', 'span', 'strong', 'style', 'use']
    no_new_line_list = ['td']
    for t in tags:
        N = f'<{t.name} '
        if t.name not in stop_list:
           s = t.string
           if t.name == 'p':
                 s = t.get_text()
           if s is None:
             s = ''  
           else:
             s = f' {s}'
           if t.name in no_new_line_list:
                ch_count=0
                for c in  t.children:
                    ch_count += 1   
                if ch_count == 0:
                    complete_text = f'{complete_text} {N}{s}>'
                else:
                    continue
           else: 
                if t.name in ['p', 'img', 'svg']:
                    complete_text = f'{complete_text} {N}{s}>'
                else:  
                    complete_text = f'{complete_text}\n{N}{s}>'
                if t.name in ['p']:
                     if t.context is not None:
                         print(t.context)
    complete_text = replace_drop_words_by_stab(complete_text, DROP_WORDS, "")
    complete_text = re.sub(r'<br/>', ' ', complete_text)
    complete_text = re.sub(r'<br >', ' ', complete_text)
    #complete_text = re.sub(r'<tr >', '| ', complete_text)
    #complete_text = re.sub(r'<p  >', '| ', complete_text)
    #complete_text = re.sub(r'> <p', '| ', complete_text)
    #complete_text = re.sub(r'<tr \|', '| ', complete_text)
    page_counter = 1
    return complete_text, page_counter
    complete_text = f'{complete_text}\n---------------------------------------------\n'
    title = soup.find('title')
    txt = f'<{TITLE_TAG}>\n{title.string}\n</{TITLE_TAG}>\n'
    txt = replace_drop_words_by_stab(txt, DROP_WORDS, "")
    complete_text = f'{complete_text}\n{txt}'
    txt = soup.get_text('\n')
    txt = replace_drop_words_by_stab(txt, DROP_WORDS, "")
    txt = re.sub(r'\x20+', ' ', txt)
    txt = re.sub(r'\n\x20+', '\n', txt)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    #print(complete_text)     
    #get_tables(filename)
    exit(0)
    title = soup.find('title')
    print(title.string + '\n')
    #paragraphs = soup.findAll('p', href=True)
    paragraphs = soup.findAll('p')
    for paragraph in paragraphs:
        if paragraph.string is not None:  
            complete_text = f'{complete_text}\n{paragraph.string}'
        else:
            complete_text = f'{complete_text}\n'
    print(complete_text) 
    exit(0)
    return "", 1

    with pdfplumber.open(filename) as html:
        pages = html.pages
        for page in pages:
            txt = page.extract_text(layout=True)
            txt = replace_drop_words_by_stab(txt, DROP_WORDS, "")
            txt = f'{txt}{page_separator}'
            complete_text = f'{complete_text}{txt}'
            page_counter += 1
    return complete_text, page_counter


def build_single_txt_doc(filename: str, mode: str = '',
                         page_separator: str = '\n\n') -> int:
    if not filename.endswith(".html"):
        raise ValueError(f'Not a html file: {filename}')
    print(f"\nDocument file: {filename}")
    page_counter = 0
    complete_text, page_counter = build_flat_txt_doc(filename,
                                                     SENTENCE_SEPARATOR)
    print(f'Symbols in document: {len(complete_text)}')
    print(f'Page_counter: {page_counter}')
    output_filename = filename.replace(".html", ".txt")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"{complete_text}")
    return "", 1

    doc_name = count_phrase_frequency(complete_text, page_counter)

    complete_text = ''
    source_name = ''
    output_filename = filename.replace(".html", ".txt")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"<{DOCUMENT}>\n{filename}\n</{DOCUMENT}>\n")
    print(f'Document name from page headers: <{doc_name}>')
    current_page = get_page_numbers_list(filename)
    with pdfplumber.open(filename) as html:
        pages = html.pages
        local_page_counter = 0
        for index, page in enumerate(pages):
            txt = page.extract_text(layout=True)

            if mode == 'flat':
                txt = replace_drop_words_by_stab(txt, DROP_WORDS, "")
            else:
                txt = replace_drop_words_by_stab(txt, DROP_WORDS)
                if index == 0:
                    txt = re.sub(r'\s+', ' ', txt)
                    source_name = txt.replace(STAB, ' ')
                    source_name = re.sub(r'_{2,}', ' ', source_name)
                    txt = f'{doc_name}\n<{PAGE_HEADER_END}>\n{txt}\nСтраница 0 из 0\n'
                txt = replace_space_lines_with_linebreaks(txt)
                txt = txt.replace(STAB, ' ')
                if current_page is None:
                    txt = smart_mark_page_numbers(txt)
                else:
                    txt = simple_mark_page_numbers(txt, current_page)
                    current_page += 1

                txt = mark_page_headers_2(txt, doc_name)
                txt = set_paragraph_borders(txt)
                txt = mark_chunks_on_page(txt, source_name)
            txt = f'{txt}\n{page_separator}'
            complete_text = f'{complete_text}{txt}'
            local_page_counter += 1
            page_counter += 1
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write(f"\n{txt}\n")
        print(f"{local_page_counter} pages found.")
    return complete_text, page_counter


def get_tables(filename):
    tables_on_page = pandas.read_html(filename)
    print ('len = ', len(tables_on_page))
    table = tables_on_page[0]
    table.to_json("table.json", index=False, orient='table')
    print(table)


def build_txt(mode: str = '', page_separator: str = '') -> int:
    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
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
        if page_separator == '':
            build_single_txt_doc(filename, mode)
        else:
            build_single_txt_doc(filename, mode, page_separator)

def parse_html():
    # Получаем содержимое страницы
    response = requests.get(url)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    # Находим все ссылки на странице
    links = soup.findAll('a', href=True)
    for link in links:
       # href = link['href']
       # if re.search(regex, link):
       #if 'a' in link.get_text():
       if 'ГОСТ' in  link.get_text(): 
            href = link['href']
            print(href)
            # if re.search(regex, href):
            # Скачиваем страницу
            target_page = requests.get('https://docs.cntd.ru' + href)
            
            with open(f'downloads{href}.html', 'wb') as f:
                f.write(target_page.content)

if __name__ == "__main__":
    regex = r'\bГОСТ\b'
    # parse_html()
    build_txt()
