# MetalloInfoBot
Reference system based on AI (RAG+LLM) t.me/RadostTrudaMetalloInfoBot. 


## Preparations
1. Setup virtual environment.
    ``` 
    python3.11 -m venv venv
    source venv/bin/activate
    ```
1. Setup dependencies:
    ```
    pip install --upgrade pip
    pip install -r tlgbotcore/requirements.txt
    pip install -r ./requirements.txt
    ```
1. Download embedding model hudlit to folder emb_models:
```
wget https://storage.yandexcloud.net/natasha-navec/packs/navec_hudlit_v1_12B_500K_300d_100q.tar  -P ./emb_models --directory-prefix=./emb_models 
```    

1. Create database for chat history in db directory:
    ```
    sqlite3
    sqlite> .open db/MetalloInfoBot.db
    sqlite> .exit
    ```

1. Download reference data:
    ```
    python3 download_gosts.py
    ```

1. Convert reference html-data to text-format:

    ```
    python3 html_to_txt.py
    ```
1. Convert reference data to md-format.
   Put reference data in md-format to directory: knowledge/

1. Mark up md-data by tags marking chunks and meta data:

    ```
    gost_md_to_md.py
    ```

    Copy `*_chunked.md` files to *knowledge/metalloprokat* directory.

    Generate tables descriptions (script development is not finished): 
    ```
    chunked_md_to_metatable.py
    ```
1.  Make and put chunks to vector db.
    ```
    source vector_data_gen.sh    
    ```

1. In separate console run a vector database (*chromaDB*):
    ```
    source MotobikeServiceBot/run_vector_db.sh 
    ```

1. Put reference data (text) as chunks to the vector database (*chromaDB*):
    ```
    source ./vector_data_gen.sh 
    ```

## Run Telegram Bot or Local Chat

### Telegram Bot
```
source bot.sh
```

### Local Chat
```
python model_io.py
```
