import embeddings_ctrl as ec
import os
import chunk_ctrl as cc
import ollama, chromadb, time
from mattsollamatools import chunk_text_by_sentences
import config
from os import listdir
from os.path import isfile, join
from navec_embedding_function import NavecEmbeddingFunction
import argparse
import ast

# Load settings from configuration file.
DEFAULT_SETTINGS_FILE = 'models.cfg'
cfg = config.Config(DEFAULT_SETTINGS_FILE)
#EMBED_MODEL = cfg["embedmodel"]
#MAIN_MODEL = cfg["mainmodel"]
#USE_CHAT = cfg['use_chat']
COLLECTION_NAME = cfg['collection_name']
#PRINT_CONTEXT = cfg['print_context']
CHROMA_PORT = cfg['chroma_port']
USE_EXTERNAL_EMBEDDING = cfg['use_external_embedding']


def chunk_text_by_tags(source_text, tag_of_begin: str,
                       tag_of_end: str = '',
                       overlap: int = 0) -> list[str]:

    data = source_text.split(tag_of_begin)
    cleaned_data = [item.strip() for item in data if item]
    return cleaned_data


def delete_collection() -> int:
    chroma_client = chromadb.HttpClient(host="localhost", port=CHROMA_PORT)
    print(chroma_client.list_collections())
    if any(
        collection.name == COLLECTION_NAME
        for collection in chroma_client.list_collections()
    ):
        print("deleting collection")
        chroma_client.delete_collection(COLLECTION_NAME)
        

def build_collection() -> int:
    delete_collection() 
    chroma_client = chromadb.HttpClient(host="localhost", port=CHROMA_PORT)
    if USE_EXTERNAL_EMBEDDING is True:
        collection = chroma_client.get_or_create_collection(
                                                            name=COLLECTION_NAME,
                                                            metadata={"hnsw:space": "cosine"}
                                                           )
    else:
        collection = chroma_client.get_or_create_collection(
                                                        name=COLLECTION_NAME,
                                                        #metadata={"hnsw:space": "cosine"},
                                                        #metadata={"hnsw:space": "l2"},
                                                        metadata={"hnsw:space": "ip"},
                                                        embedding_function=NavecEmbeddingFunction()
                                                       )

    print(f'{EMBED_MODEL} embeddings selected.')

    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    # Temporary jast two files parsing.
    #files = ['1200108697.txt', '1200113779#7D20K3.txt']
    #files = ['ГОСТ 14637-89 (ИСО 4995-78).txt', 'ГОСТ 19281-2014.txt']
    # files = ['ГОСТ 14637-89 (ИСО 4995-78).md', 'ГОСТ 19281-2014.md']
    # https://docs.cntd.ru/document/1200113779
    # https://docs.cntd.ru/document/1200000119
    text = ''
    chunks_counter = 0
    for path in files:
        if not path.endswith(".md"):
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
            odd_chunks = chunk_text_by_tags(
                source_text=text.replace(EVEN_BEGIN_TAG, " "), tag_of_begin=ODD_BEGIN_TAG)
            even_chunks = chunk_text_by_tags(
                source_text=text.replace(ODD_BEGIN_TAG, " "), tag_of_begin=EVEN_BEGIN_TAG)
            odd_chunks.extend(even_chunks)
            chunks = odd_chunks

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
            
            num = cc.read_tag(chunk, cc.CHUNK_NUMBER)
            print(num)
            context = cc.read_tag(chunk, cc.CHUNK_QUOTE)
            print("context")
            print(context)
            context = context.replace('\___\___\___', ' ')
            context = context.replace('\___\___\____', ' ')
            context = context.replace('_', " ")
            context = context.replace('таблица_без_имени', 'таблица')
            context = context.strip()
           
            # Пустой контекст приводит к падению.
            if len(context) < 1:
                continue
            
            # Пустой контекст состоит только из чисел это приводит к падению.
            ctx = context.replace(' ', "")
            if all(char.isdigit() or char == '.' or char == ',' for char in ctx):
                continue
            if "<chunk_src" in context:
                exit(0)

            if EMBED_MODEL == "navec":
                print(index, context)
                embed = ec.navec_embeddings(context)["embedding"]
            else:
                embed = ollama.embeddings(model=EMBED_MODEL, prompt=context)[
                    "embedding"
                ]

            metas = cc.read_tag(chunk, cc.CHUNK_META)
            if len(metas) == 0:
                metas = None 
            else:
                metas = ast.literal_eval(metas)
            print('metas =', metas)
            
            ids = cc.read_tag(chunk, cc.CHUNK_IDS)
            print('ids = !', ids, "!")
            if USE_EXTERNAL_EMBEDDING is True:
                collection.add(
                    [filename + str(index)],
                    [embed],
                    documents=[context], # [chunk]
                    metadatas=[metas] # metadatas={"source": filename},
                    )
            else:
                collection.add(
                    ids=[filename + str(index)],
                    documents=[context],
                    metadatas=[metas]
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
    global ODD_BEGIN_TAG
    ODD_BEGIN_TAG = cfg['odd_begin_tag']
    global EVEN_BEGIN_TAG
    EVEN_BEGIN_TAG = cfg['even_begin_tag']
    global CHUNKING
    CHUNKING = cfg['chunking']
    
    global SPLIT_BY_PARAGRAPHS
    SPLIT_BY_PARAGRAPHS = cfg['split_by_paragraphs']
    print(f'Collection name: {COLLECTION_NAME}')
    if cli_args.d:
        delete_collection() 
        exit(0)



def parse_args():
    """CLI options parsing."""

    prog_name = os.path.basename(__file__).split(".")[0]

    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="Data generator for vector base ChromaDB.",
        epilog="Text at the bottom of help",
    )
    parser.add_argument("-m", dest="models_config",
                        help="Model configuration file path.")
    parser.add_argument("-d",  action="store_true",
                        help="Delete dataset.")
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
