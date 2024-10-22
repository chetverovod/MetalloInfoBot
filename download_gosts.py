import requests
from bs4 import BeautifulSoup
import config
import re

# Load settings from configuration file.
cfg = config.Config('html_to_txt.cfg')
REF_DOCS_PATH = cfg['reference_docs_path']

def find_and_download_links(url, regex):
    # Получаем содержимое страницы
    response = requests.get(url)

    if not response.ok:
        print("Ошибка при получении страницы.")
        return

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

            path = REF_DOCS_PATH
            path = f'{path}{href.replace("document/", "")}.html'
            print (path)
            with open(path, 'wb') as f:
                f.write(target_page.content)

if __name__ == "__main__":
    #url = input("Введите URL страницы: ")
    url_list = ['https://docs.cntd.ru/document/1200113779',
                'https://docs.cntd.ru/document/1200000119']
    print(f'URL страницы: {url_list}')
    regex = r'\bГОСТ\b'
    for url in url_list:
       find_and_download_links(url, regex)

