import sys
import logging
import embeddings_ctrl as ec
import ollama
import chromadb
from chromadb.types import SegmentScope
from navec_embedding_function import NavecEmbeddingFunction
import config
import gc
import os
import psutil

# Load settings from configuration file.
DEFAULT_SETTINGS_FILE = 'models.cfg'
cfg = config.Config(DEFAULT_SETTINGS_FILE)
EMBED_MODEL = cfg["embedmodel"]
MAIN_MODEL = cfg["mainmodel"]
USE_CHAT = cfg['use_chat']
COLLECTION_NAME = cfg['collection_name']
PRINT_CONTEXT = cfg['print_context']
CHROMA_PORT = cfg['chroma_port']

def bytes_to_gb(bytes_value):
    return bytes_value / (1024 ** 3)


def get_process_info():
    pid = os.getpid()
    p = psutil.Process(pid)
    with p.oneshot():
        mem_info = p.memory_info()
        # disk_io = p.io_counters()
    return {
        "memory_usage": bytes_to_gb(mem_info.rss),
    }


def unload_index(collection_name: str, chroma_client: chromadb.PersistentClient):
    """
    Unloads binary hnsw index from memory and removes both segments (binary and metadata) from the segment cache.
    """
    collection = chroma_client.get_collection(collection_name)
    collection_id = collection.id
    #segment_manager = chroma_client._server._manager
    segment_manager = chroma_client._server.chroma_segment_manager_impl
    for scope in [SegmentScope.VECTOR, SegmentScope.METADATA]:
        if scope in segment_manager.segment_cache:
            cache = segment_manager.segment_cache[scope].cache
            if collection_id in cache:
                segment_manager.callback_cache_evict(cache[collection_id])
    gc.collect()


def get_collection(collection_name: str = None) -> chromadb.Collection:
    """
    Creates and returns a Chroma collection. Collection contains reference
    documents and corresponding embeddings.

    Returns:
        chromadb.Collection: A Chroma collection.
    """

    chroma = chromadb.HttpClient(host="localhost", port=CHROMA_PORT)
    collection = chroma.get_or_create_collection(collection_name,
                                                 embedding_function=NavecEmbeddingFunction())
    return collection


def free_mem_collection(collection_name: str = None) -> None:
    """
    Free memory from a Chroma collection.

    Args:
        collection_name (str, optional): Name of the Chroma collection. Defaults to None.
    """

    chroma_client = chromadb.HttpClient(host="localhost", port=CHROMA_PORT)
    unload_index(collection_name, chroma_client)


def build_prompt(user_query: str, rag_context: str) -> str:
    """Build prompt for LLM model."""

    prompt = BASE_FOR_PROMPT.replace('<user_query>', user_query)
    prompt = prompt.replace('<rag_context>', rag_context)

    #prompt = prompt.replace('<conversation_history>', ' '.join(flat_book))
    #logging.info('conversation_book: %s', conversation_book)
    return prompt


def get_rag_context(query: str, config_file: str) -> str:
    """Get reference text."""

    cfg = config.Config(config_file)
    global EMBED_MODEL
    EMBED_MODEL = cfg["embedmodel"]
    global MAIN_MODEL
    MAIN_MODEL = cfg["mainmodel"]
    global USE_CHAT
    USE_CHAT = cfg['use_chat']
    global COLLECTION_NAME
    COLLECTION_NAME = cfg['collection_name']
    global PRINT_CONTEXT
    PRINT_CONTEXT = cfg['print_context']
    global BASE_FOR_PROMPT
    BASE_FOR_PROMPT = cfg['base_for_prompt']

    collection = get_collection(COLLECTION_NAME)
    print('config:', config_file)
    print(collection)
    """
    if EMBED_MODEL == 'navec':
        emb = ec.navec_embeddings(query)
    else:
        emb = ollama.embeddings(model=EMBED_MODEL, prompt=query)
    queryembed = emb["embedding"]
    relevant_docs = collection.query(
        query_embeddings=[queryembed], n_results=5)["documents"][0]
    """
    relevant_docs = collection.query(
        query_texts=(query), n_results=5)["documents"][0]

    context = "\n\n".join(relevant_docs)
    # free_mem_collection(COLLECTION_NAME)
    return context


def log_rag_context(user_query: str, rag_context: str) -> None:

    if PRINT_CONTEXT is True:
        msg = ("\n----------------------Request-------------------------\n"
                     f"{user_query}"
                     "\n----------------------Context begin-------------------\n"
                     f"docs: {rag_context}"
                     "\n----------------------Context end---------------------\n")
        logging.info(msg)
    else:
        logging.info("Skipping printing context.")


def build_flat_book(user_query: str, prompt: str,
                    history_book: list[str]) -> list[str]:
    """ Build flat book."""
    flat_book = []
    for question, answer in history_book:
        flat_book.append(question)
        flat_book.append(answer)
    main_phrase = {
                   'role': 'user',
                   'content': user_query,
                   'prompt': prompt
                  }
    flat_book.append(main_phrase)
    logging.info("flat book %s", flat_book)
    logging.info("flat book size (bytes): %s", sys.getsizeof(flat_book))
    return flat_book


def get_answer(user_query: str, models_config_file: str,
               history_book: list[str]) -> str:
    """ Make single answer."""

    rag_context = get_rag_context(user_query, models_config_file)
    if len(rag_context) == 0:
        logging.info("RAG context is empty fo query: %s", user_query)

    prompt = build_prompt(user_query, rag_context)
    log_rag_context(user_query, rag_context)
    flat_book = build_flat_book(user_query, prompt, history_book)

    if USE_CHAT is True:
        logging.info('<chat> mode')
        NUM_CTX = 4096 #2048
        opt = {"num_ctx": NUM_CTX}
        #response = ollama.chat(model=MAIN_MODEL, messages=flat_book, options=opt)
        response = ollama.chat(model=MAIN_MODEL, messages=flat_book)
        res = response['message']['content']
    else:
        logging.info('<generate mode> mode')
        stream = ollama.generate(model=MAIN_MODEL, prompt=prompt,
                                 stream=True)
        res = ''
        for chunk in stream:
            if chunk["response"]:
                res += chunk['response']
    logging.info(res)
    return res


def main():
    """
    The main function.
    """

    run_flag = True
    logging.info("%s", f'Embedding model: {EMBED_MODEL}')
    logging.info("%s", f'Main model: {MAIN_MODEL}')

    print('\nAssistant is running.\n'
                 'Enter your question or type "q" to exit.\n')
    if USE_CHAT is True:   
        print('mode: <chat>')
    else:
        print('mode: <generate>')
    
    if EMBED_MODEL == 'navec':
        logging.info('Navec embeddings selected.\nType questions in Russian.\n')

    answer_tag = ">>> "
    query_tag = "<<< "

    while run_flag is True:
        query = input(query_tag)
        if query.capitalize() != 'Q' and query.capitalize() != 'Й':
            rag_context = get_rag_context(query, DEFAULT_SETTINGS_FILE)
            modelquery = build_prompt(query, rag_context)
            log_rag_context(query, rag_context)

            if USE_CHAT is True:
                response = ollama.chat(model=MAIN_MODEL, messages=[
                    {
                        'role': 'user',
                        'content': query,
                        'prompt': modelquery
                    },
                ])

                print(response['message']['content'])
            else:
                stream = ollama.generate(model=MAIN_MODEL, prompt=modelquery,
                                         stream=True)
                print(f'{answer_tag} Thinking...', end="", flush=True)
                #print(f'\nrag_context:{rag_context}', end="", flush=True)
                shift_back_cursor = True
                for chunk in stream:
                    if chunk["response"]:
                        if shift_back_cursor is True:
                            print(f'\r{answer_tag}', end="", flush=True)
                            shift_back_cursor = False
                        print(chunk["response"], end="", flush=True)

            print("\n")
        else:
            print("Exit.")
            run_flag = False


if __name__ == "__main__":
    main()
