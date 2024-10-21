import torch
import numpy
from navec import Navec
from slovnet.model.emb import NavecEmbedding
import string

navec = Navec.load("emb_models/navec_hudlit_v1_12B_500K_300d_100q.tar")


def navec_embeddings(text):
    """
    This function generates a navec embedding for a given text.

    It takes a string `text` as input, preprocesses it by removing punctuation, 
    digits, and extra whitespace, and then converts it to lowercase.

    The function uses the `Navec` model to generate embeddings for each word in 
    the text. If a word is not found in the `Navec` vocabulary, it uses the 
    unknown token ('<unk>') instead.

    The function returns a dictionary with a single key 'embedding' that 
    contains the normalized sum of the word embeddings as a list.
    """

    data = text
    translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
    data = data.translate(translator)
    translator = str.maketrans(string.whitespace, ' ' * len(string.whitespace))
    data = data.translate(translator)
    translator = str.maketrans(string.digits, ' ' * len(string.digits))
    data = data.translate(translator)

    data = data.lower()
    data = data.replace("   ", " ")
    data = data.replace("  ", " ")
    data = data.split(" ")
    data = list(filter(None, data))
    emb = NavecEmbedding(navec)
    ids = []
    for word in data:
        if word in navec:
            ids.append(navec.vocab[word])
        else:
            ids.append(navec.vocab['<unk>'])

    in_data = torch.tensor(ids.copy())
    e = emb(in_data)
    norm = torch.sum(e, dim=0)/e.shape[0]
    res = norm.tolist()
    return {"embedding": res}
