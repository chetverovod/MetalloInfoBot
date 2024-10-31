import chromadb
#from src.embd_func import NavecEmbeddingFunction
from embd_func import NavecEmbeddingFunction


class Chromadb_api():
    def __init__(self):
        self.collection = self.load_db()


    def load_db(
        self,
        bd_path: str="./chromadb/chromadb",
        collection_name: str="metalloprokat"
    ) -> None:
        self.collection = chromadb.PersistentClient(
            path=bd_path).get_collection(
                name=collection_name,
                embedding_function=NavecEmbeddingFunction()
        )


    def query_to_db(
            self,
            question: str,
            filter_list: list,
            n_results: int=40
            ) -> str:
        """
        Запросы в базу с фильтрацией метаданных рекурсивно с уменьшением фильтра
        """
        if not hasattr(self, 'collection'):
            self.load_db()
        if len(filter_list) == 1:
             meta_filter = filter_list[0]
        else:
            meta_filter = {"$and": filter_list}
        results = self.collection.query(
            query_texts=question,
            where = meta_filter,
            n_results=n_results
        )
        if len(results['ids'][0]):
            return results
        else:            
            results = self.query_to_db(question, filter_list[1:])