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

    def create_index(self, questions, queries, index_file='text_to_sql_index.faiss'):
        """
        Create a FAISS index from the given questions and queries.

        Parameters:
        - questions (list): List of user input text.
        - queries (list): List of corresponding SQL queries.
        - index_file (str): Filename for saving the FAISS index. Default is 'text_to_sql_index.faiss'.
        """
        self.questions = questions
        self.queries = queries
        print(questions[0])
        print(len(questions))

        try:
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

            # Optionally write the index to a file
            faiss.write_index(self.index, index_file)
            print(f"Index successfully saved to {index_file}")

        except Exception as e:
            print(f"An error occurred while creating the index: {e}")

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
