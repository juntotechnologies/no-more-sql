import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class FAISSIndex:
    """
    Class to handle FAISS indexing and retrieval.
    """

    def __init__(self, model_path):
        """
        Initialize FAISSIndex object.

        Parameters:
        - model_path (str): Path to the Sentence Transformer model.
        """
        self.model = SentenceTransformer(model_path)
        self.index = None
        self.sentences = []

    def create_index(self, sentences):
        """
        Create a FAISS index from the given sentences.

        Parameters:
        - sentences (list): List of sentences for context.
        """
        self.sentences = sentences
        embeddings = self.model.encode(sentences)
        # Create FAISS index
        dim = len(embeddings[0])
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(np.array(embeddings, dtype=np.float32))

    def retrieve_top_k(self, query, k=5):
        """
        Retrieve top K sentences based on a query.

        Parameters:
        - query (str): User query.
        - k (int): Number of nearest neighbors to retrieve.

        Returns:
        - list: Top K retrieved sentences as context.
        """
        query_vector = self.model.encode(query)
        # Search the FAISS index
        distances, indices = self.index.search(np.array([query_vector], dtype=np.float32), k)

        # Retrieve corresponding sentences
        context = [self.sentences[index] for index in indices[0]]
        context = "\n".join(context)
        return context
