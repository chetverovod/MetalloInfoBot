import embeddings_ctrl as ec
import os
import ollama, chromadb, time
from mattsollamatools import chunk_text_by_sentences
from model_tools import split_into_parts, split_into_paragraphs, split_into_paragraphs2
import config
from os import listdir
from os.path import isfile, join
import argparse


def chunk_text_by_tags(source_text, tag_of_begin: str,
                       tag_of_end: str = '',
                       overlap: int = 0) -> list[str]:

    data = source_text.split(tag_of_begin)
    cleaned_data = [item.strip() for item in data if item]
    return cleaned_data


def build_collection() -> int:
    chroma = chromadb.HttpClient(host="localhost", port=8000)
    print(chroma.list_collections())
    if any(
        collection.name == COLLECTION_NAME
        for collection in chroma.list_collections()
    ):
        print("deleting collection")
        chroma.delete_collection(COLLECTION_NAME)
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    print(f'{EMBED_MODEL} embeddings selected.')

    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    # Temporary jast two files parsing.
    #files = ['1200108697.txt', '1200113779#7D20K3.txt']
    files = ['ГОСТ 14637-89 (ИСО 4995-78).txt', 'ГОСТ 19281-2014.txt']
    # https://docs.cntd.ru/document/1200113779
    # https://docs.cntd.ru/document/1200000119
    text = ''
    chunks_counter = 0
    for path in files:
        if not path.endswith(".txt"):
            continue
        relative_path = REF_DOCS_PATH + '/' + path
        filename = os.path.abspath(relative_path)
        print(f"\nDocument: {filename}")
        with open(filename, "rb") as f:
            text = f.read().decode("utf-8")

        if CHUNKING == 'by_sentences':
            chunks = chunk_text_by_sentences(
                source_text=text, sentences_per_chunk=7, overlap=0)
        elif CHUNKING == 'by_tags':
            chunks = chunk_text_by_tags(
                source_text=text, tag_of_begin=BEGIN_TAG)
        else:
            raise ValueError(
                f"CHUNKING must be 'by_sentences' or 'by_tags', not {CHUNKING}"
            )

        print(f"{len(chunks)} chunks")

        if SPLIT_BY_PARAGRAPHS:
            chunks = text.replace('</paragraph>', '').split('<paragraph>')
            chunks.remove(chunks[-1])  # remove empty []     
        
        chunks_counter += len(chunks)

        for index, chunk in enumerate(chunks):
            if EMBED_MODEL == "navec":
                embed = ec.navec_embeddings(chunk)["embedding"]
            else:
                embed = ollama.embeddings(model=EMBED_MODEL, prompt=chunk)[
                    "embedding"
                ]
            print(f"{index} {chunk}")    
            print(".", end="", flush=True)

            collection.add(
                [filename + str(index)],
                [embed],
                documents=[chunk],
                metadatas={"source": filename},
                )
    return chunks_counter


def init(cli_args: dict):
    """Initial settings for start."""
    # Load settings from configuration file.
    global cfg
    # cfg = config.Config('models.cfg')
    cfg = config.Config(cli_args.models_config)
    global EMBED_MODEL 
    EMBED_MODEL = cfg["embedmodel"]
    global COLLECTION_NAME
    COLLECTION_NAME = cfg['collection_name']
    global REF_DOCS_PATH
    REF_DOCS_PATH = cfg['reference_docs_path']
    global BEGIN_TAG
    BEGIN_TAG = cfg['begin_tag']
    global CHUNKING
    CHUNKING = cfg['chunking']
    
    global SPLIT_BY_PARAGRAPHS
    SPLIT_BY_PARAGRAPHS = cfg['split_by_paragraphs']
    print(f'Collection name: {COLLECTION_NAME}')

def parse_args():
    """CLI options parsing."""

    prog_name = os.path.basename(__file__).split(".")[0]

    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="Telegram bot.",
        epilog="Text at the bottom of help",
    )
    parser.add_argument("-m", dest="models_config",
                        help="Model configuration file path.")
    return parser.parse_args()


global args
args = parse_args()
print(f"args: {args}")
init(args)
# print(f"Bot <{cfg['bot_name']}>  started. See log in <{cfg['log_file']}>.")

start_time = time.time()
chunks = build_collection()
print(f"\n{chunks} chunks found.")
print(f"\n--- {time.time() - start_time} seconds ---")
