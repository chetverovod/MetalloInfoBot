import re


def split_into_parts(text, part_size=1000):
    """
    Функция делит длинный текст, который кроме прочего содержит и нумерованные
    списки с точкой после номера, на несколько частей заданной длины по границе
    предложения.
    """

    sentences = re.findall(r'\s*([^.\d].+?)(\.|\s+$)', text)
    parts = []
    current_part = ''
    i = 0
    while i < len(sentences):
        sentence = sentences[i][0]
        if len(current_part) + len(sentence) > part_size:
            parts.append(current_part)
            current_part = sentence
        else:
            current_part += sentence
        i += 1
    parts.append(current_part)
    return parts


def split_into_paragraphs(text):
    paragraphs = re.findall(r'(?<=\n)(.*?)(?=\n\n|$)', text)
    cleaned_paragraphs = []
    for paragraph in paragraphs:
        if not re.match(r'\d+\.', paragraph):
            cleaned_paragraphs.append(paragraph)
    return cleaned_paragraphs


def split_into_paragraphs2(text):
    paragraphs = re.findall(r'(?<=\n)(.*?)(?=\n\n|$)', text)
    numbered_lists = {}
    for paragraph in paragraphs:
        lists = re.findall(r'^(.*?)\n\d+\.', paragraph)
        if lists:
            numbered_lists[paragraph] = lists[-1]
    final_parts = []
    for paragraph in paragraphs:
        if paragraph in numbered_lists:
            final_parts.append(f"{paragraph}\n{numbered_lists[paragraph]}")
        else:
            final_parts.append(paragraph)
    return final_parts