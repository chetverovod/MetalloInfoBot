# MetalloInfoBot
Reference system based on AI (RAG+LLM) t.me/RadostTrudaMetalloInfoBot. 


## Preparations
1. Setup virtual environment.
    ``` 
    python3.11 -m venv venv
    source venv/bin/activate
    ```
1. Setup dependacies:
    ```
    pip install --upgrade pip
    pip install -r MotobikeServiceBot/requirements.txt
    pip install -r ./requirements.txt
    ```
1. Download emdedding model hudlit to folder emb_models:
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

1. Convert reference data to text:
    ```
    python3 html_to_txt.py
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
