import logging
import pandas as pd
from faiss_indexing_retrieval import FAISSIndex
import ollama

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Scripts:
    def __init__(self, model_name='sentence-transformers/all-MiniLM-L6-v2', csv_file='data/prompt_sql.csv'):
        logger.info("Initializing FAISS Index")
        self.faiss_index = FAISSIndex(model_name)
        self.questions, self.queries = self.load_sentences(csv_file)
        self.faiss_index.create_index(self.questions, self.queries)

    def load_sentences(self, csv_file):
        """Load questions and queries from a CSV file."""
        try:
            df = pd.read_csv(csv_file)
            print(df.head())
            return df['prompt'].tolist(), df['completion'].tolist()
        except Exception as e:
            logger.error(f"Failed to load sentences: {e}")
            return [], []

    def generate_response(self, user_input, prev_messages, k):
        """Generate a SQL response based on user input and previous messages."""
        logger.info("Generating response")
        
        # Retrieve context from the FAISS index
        context = self.faiss_index.retrieve_top_k(user_input, k=2)
        
        # Format previous messages
        formatted_prev_msgs = "\n".join(f"{msg['role']}: {msg['content']}" for msg in prev_messages)
        
        # Create the instruction for Ollama
        instruction = (
            "You are an expert at writing SQL codes. Based on the user query and the following examples, "
            f"write the SQL code. ### input: {user_input}\n"
            "**Examples:**\n" + "".join(context) + 
            f"\n### output:"
        )
        
        logger.info("Calling Ollama API")
        logger.info(instruction)
        # Call the Ollama API
        try:
            response = ollama.chat(model='llama3.1', messages=[{'role': 'user', 'content': instruction}], stream = True)
            stream = [" ".join(chunk['message']['content']) for chunk in response]
            text = "".join(stream)
            print(type(text))
            return text
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return "Error generating response."

# Example usage
# script = Scripts()
# response = script.generate_response("Your SQL query here", previous_messages, top_k)
