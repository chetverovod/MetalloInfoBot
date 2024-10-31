import string
import torch
from navec import Navec
from slovnet.model.emb import NavecEmbedding
import chromadb
from chromadb.api.types import EmbeddingFunction


class NavecEmbeddingFunction(EmbeddingFunction):
    def __init__(
            self,
            model_name: str = "navec_hudlit_v1_12B_500K_300d_100q.tar",
            model_path: str = './models/'
    ):
            self.navec = Navec.load(model_path + model_name)

    @staticmethod
    def _preprocess(text: str) -> list:
        """Предобработка текста"""
        text = text.translate(
            str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
        text = text.translate(
            str.maketrans(string.whitespace, ' ' * len(string.whitespace)))
        text = text.translate(
            str.maketrans(string.digits, ' ' * len(string.digits)))
        text = text.lower()
        text = text.replace("   ", " ")
        text = text.replace("  ", " ")
        text = text.split(" ")
        text = list(filter(None, text))
        return text

    def _tokenizer(self, words: list) -> torch.tensor:
        """Токенизируем список слов с помощью модели Navec"""
        in_data = torch.tensor(words)
        return NavecEmbedding(self.navec)(in_data)

    @staticmethod
    def _normalize(vector):
        """Нормализация векторов эмбеддингов"""
        return torch.sum(vector, dim=0) / vector.shape[0]

    def __call__(self, input: list) -> list:
        """Обрабатываем входящие документы по списку"""
        out_list = []
        for document in input:
            document = self._preprocess(document)
            words = []
            for word in document:
                if word in self.navec:
                    words.append(self.navec.vocab[word])
                else:
                    words.append(self.navec.vocab['<unk>'])
            embeddings = self._tokenizer(words)
            norm_embeddings  = self._normalize(embeddings)
            out_list.append(norm_embeddings)
        return out_list