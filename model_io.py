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
from src.chain_of_thoughts import Chain_of_thoughts
from src.vbd_api import Chromadb_api
#from src.llama_model_api import Llama_api
from src.ollama_model_api import Llama_api
#from src.gigachat_api import Giga_chat


# Load settings from configuration file.
DEFAULT_SETTINGS_FILE = 'models.cfg'
cfg = config.Config(DEFAULT_SETTINGS_FILE)
EMBED_MODEL = cfg["embedmodel"]
MAIN_MODEL = cfg["mainmodel"]
USE_CHAT = cfg['use_chat']
COLLECTION_NAME = cfg['collection_name']
PRINT_CONTEXT = cfg['print_context']
CHROMA_PORT = cfg['chroma_port']
USE_EXTERNAL_EMBEDDING = cfg['use_external_embedding']


# Включаем логирование, чтобы не пропустить важные сообщения
if PRINT_CONTEXT is True:
    logging.basicConfig(level=logging.INFO, filename='model_io.log',
                        filemode="w")


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


def build_prompt(rag_context: str) -> str:
    """Build prompt for LLM model."""

    #prompt = BASE_FOR_PROMPT.replace('<user_query>', user_query)
    prompt = BASE_FOR_PROMPT
    prompt = prompt.replace('<rag_context>', rag_context)
    logging.info("prompt: %s", prompt)
    #prompt = prompt.replace('<conversation_history>', ' '.join(flat_book))
    #logging.info('conversation_book: %s', conversation_book)
    return prompt


def get_rag_context(query: str, config_file: str, n_results=5) -> str:
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

    if USE_EXTERNAL_EMBEDDING is True:
        if EMBED_MODEL == 'navec'     :
            emb = ec.navec_embeddings(query)
        else:
            emb = ollama.embeddings(model=EMBED_MODEL, prompt=query)
        queryembed = emb["embedding"]
        qres = collection.query(
            query_embeddings=[queryembed], n_results=n_results)
    else:
        qres = collection.query(query_texts=(query), n_results=n_results)

    logging.info('query: %s', query)
    logging.info('\n--------------------------------------------------------\n')
    s = qres['distances'][0]
    d = qres['documents'][0]
    for score, doc in zip(s, d):
        logging.info(score)
        logging.info(doc)
        logging.info('\n--------------------------------------------------------\n')
    relevant_docs = qres["documents"][0]
    
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
    sytem_msg = {
                 'role': 'system',
                 'content': prompt
                }
    flat_book = [sytem_msg]
    for question, answer in history_book:
        flat_book.append(question)
        flat_book.append(answer)
    main_phrase = {
                   'role': 'user',
                   'content': user_query
                  }
    flat_book.append(main_phrase)
    logging.info("flat book %s", flat_book)
    logging.info("flat book size (bytes): %s", sys.getsizeof(flat_book))
    return flat_book


class Answer_generator(Chain_of_thoughts, Llama_api, Chromadb_api):
    pass

#class Answer_generator(Chain_of_thoughts, Giga_chat, Chromadb_api):
#    pass


def get_chain_answer(query: str) -> str:
    answer_generator = Answer_generator()
    res = answer_generator.start(query)
    return res


def get_answer(user_query: str, models_config_file: str,
               history_book: list[str]) -> str:
    """ Make single answer."""
    print(user_query)
    return get_chain_answer(user_query)
    rag_context = get_rag_context(user_query, models_config_file)
    if len(rag_context) == 0:
        logging.info("RAG context is empty fo query: %s", user_query)
    query = user_query
    prompt = build_prompt(rag_context)
    log_rag_context(user_query, rag_context)
    print(prompt)
    if USE_CHAT is True:
        flat_book = build_flat_book(user_query, prompt, history_book)
        logging.info('<chat> mode')
        #NUM_CTX = 4096 #2048
        #opt = {temprature:0, "num_ctx": NUM_CTX}
        opt = {"temperature": 0 , "seed": 42, "num_ctx": 8000}
        #response = ollama.chat(model=MAIN_MODEL, messages=flat_book, options=opt)
        if query == "Привет!":
            res = "Привет!"
        else:
            response = ollama.chat(model=MAIN_MODEL, messages=flat_book, options=opt)
            res = response['message']['content']
            low_res = res.lower()
            if ' бот' in low_res:
                res = "Мне не совсем понятен ваш вопрос."
            if ('языков' in low_res) and ('модел' in low_res):
                res = "Мне не совсем понятен ваш вопрос." 
            if ('искусственн' in low_res) and ('интеллек' in low_res):
                res = "Мне не совсем понятен ваш вопрос."
            #s = {"role": "user", "content": f'Напиши этот текст предложение в женском роде:"{res}"'}     
            #response = ollama.chat(model=MAIN_MODEL, messages=flat_book, options=opt )
    else:
        logging.info('<generate> mode')
        response = ollama.generate(model=MAIN_MODEL, prompt=f'{prompt}\n Ответь на вопрос:{query}')
        res = response["response"]
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
    print(f'embedding model: <{EMBED_MODEL}>')             
    print(f'main model: <{MAIN_MODEL}>')             
    print(f'vector collection: <{COLLECTION_NAME}>')             
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
            rag_context = get_rag_context(query, DEFAULT_SETTINGS_FILE, n_results=40)
            modelquery = build_prompt(rag_context)
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
