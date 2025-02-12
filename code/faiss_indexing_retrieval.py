import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import pickle

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
        self.index_file = 'text_to_sql_index.faiss'
        self.metadata_file = 'text_to_sql_metadata.pkl'

    def create_index(self, questions, queries):
        """Create a FAISS index from the given questions and queries."""
        self.questions = questions
        self.queries = queries
        print(questions[0])
        print(len(questions))

        try:
            # Try to load existing index first
            if self.load_index():
                return

            # Generate embeddings
            questions_embeddings = self.model.encode(self.questions)
            print("Questions Embeddings Shape:", questions_embeddings.shape)

            queries_embeddings = self.model.encode(self.queries)
            print("Queries Embeddings Shape:", queries_embeddings.shape)

            # Create FAISS index
            dim = len(questions_embeddings[0])
            self.index = faiss.IndexFlatIP(dim)

            # Stack embeddings for both questions and queries
            vectors = np.vstack((questions_embeddings.astype(np.float32), queries_embeddings.astype(np.float32)))
            self.index.add(vectors)

            # Save the index and metadata
            self.save_index()

        except Exception as e:
            print(f"An error occurred while creating the index: {e}")

    def save_index(self):
        """Save the FAISS index and metadata."""
        try:
            # Save FAISS index
            faiss.write_index(self.index, self.index_file)

            # Save metadata (questions and queries)
            with open(self.metadata_file, 'wb') as f:
                pickle.dump({
                    'questions': self.questions,
                    'queries': self.queries
                }, f)
            print(f"Index and metadata successfully saved")
            return True
        except Exception as e:
            print(f"Failed to save index: {e}")
            return False

    def load_index(self):
        """Load the FAISS index and metadata if they exist."""
        try:
            # Load FAISS index
            if not os.path.exists(self.index_file) or not os.path.exists(self.metadata_file):
                return False

            self.index = faiss.read_index(self.index_file)

            # Load metadata
            with open(self.metadata_file, 'rb') as f:
                metadata = pickle.load(f)
                self.questions = metadata['questions']
                self.queries = metadata['queries']
            print("Loaded existing index and metadata")
            return True
        except Exception as e:
            print(f"Failed to load index: {e}")
            return False

    def retrieve_top_k(self, query, k=1):
        """
        Retrieve top K sentences based on a query.

        Parameters:
        - query (str): User query.
        - k (int): Number of nearest neighbors to retrieve.

        Returns:
        - list: Top K retrieved sentences as context.
        """
        query_vector = self.model.encode(query, convert_to_tensor=True).cpu().numpy()

        # Search the FAISS index
        distances, indices = self.index.search(np.array([query_vector], dtype=np.float32), k)

        # Build context string
        context = []
        for i in range(k):
            if indices[0][i] < len(self.questions):
                similar_question = self.questions[indices[0][i]]
                similar_sql_query = self.queries[indices[0][i]]
                distance = distances[0][i]
                context.append(f"**Question:** {similar_question}\n**SQL Query:** {similar_sql_query}\n**Distance:** {distance:.4f}\n")

        return "\n".join(context)

    def __getstate__(self):
        """Return state values to be pickled."""
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        """Restore state from the unpickled state values."""
        self.__dict__.update(state)
