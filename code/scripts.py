import logging
import pandas as pd
from faiss_indexing_retrieval import FAISSIndex
import ollama
import re
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ollama.BASE_URL = "http://localhost:11434"  # Make sure this matches your Docker port mapping

class Scripts:
    def __init__(self, model_name='sentence-transformers/all-MiniLM-L6-v2', dataframe=None):
        logger.info("Initializing FAISS Index")
        self.faiss_index = FAISSIndex(model_name)

        if dataframe is not None:
            self.questions = dataframe['Prompt'].tolist()
            self.queries = dataframe['Query'].tolist()
            self.index_file = f"data/{dataframe['Source'].iloc[0]}.index"  # Define index file path based on source

            # Check if index already exists
            if not self.load_index():
                if not self.questions or not self.queries:
                    logger.error("No data to create FAISS index. Exiting initialization.")
                    return
                self.faiss_index.create_index(self.questions, self.queries)
                self.save_index()
        else:
            logger.error("No DataFrame provided to initialize Scripts.")

    def save_index(self):
        """Save the FAISS index and related data to disk"""
        try:
            import pickle
            with open(self.index_file, 'wb') as f:
                pickle.dump({
                    'questions': self.questions,
                    'queries': self.queries,
                    'index': self.faiss_index
                }, f)
            logger.info(f"Index saved to {self.index_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False

    def load_index(self):
        """Load the FAISS index and related data from disk"""
        try:
            import pickle
            if os.path.exists(self.index_file):
                with open(self.index_file, 'rb') as f:
                    data = pickle.load(f)
                    self.questions = data['questions']
                    self.queries = data['queries']
                    self.faiss_index = data['index']
                logger.info(f"Index loaded from {self.index_file}")
                return True
            else:
                logger.info("No existing index found")
                return False
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def generate_response(self, user_input, prev_messages):
        """Generate a SQL response based on user input and previous messages."""
        logger.info("Generating response")

        # Retrieve context from the FAISS index
        context = self.faiss_index.retrieve_top_k(user_input)

        # Format previous messages
        formatted_prev_msgs = "\n".join(f"{msg['role']}: {msg['content']}" for msg in prev_messages)

        # Create the instruction for Ollama
        instruction = (
            "You are an expert at writing SQL code. Based on the user query and the following examples, "
            f"write the SQL code with no extra explanation. Just the code. ### input: {user_input}\n"
            "**Examples:**\n" + "".join(context) +
            f"\n### output:"
        )

        logger.info("Calling Ollama API")
        logger.info(instruction)
        # Call the Ollama API
        try:
            response = ollama.chat(
                model='llama3.1:70b',
                messages=[{'role': 'user', 'content': instruction}],
                stream=True
            )
            stream = [chunk['message']['content'] for chunk in response]
            text = "".join(stream)

            # Post-process the text
            text = self.format_response(text)

            return text
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return "Error generating response."

    def format_response(self, text):
        """Format the response text to ensure proper SQL formatting."""
        # Remove extra spaces and clean up the text
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove any markdown or extra text that might come from the LLM
        text = re.sub(r'```sql|```|`', '', text)
        text = re.sub(r'SQL Query:|Query:|### output:', '', text)

        # List of SQL keywords to capitalize and add newlines before
        major_keywords = [
            'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY',
            'HAVING', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN',
            'UNION', 'WITH'
        ]

        condition_keywords = ['AND', 'OR']
        all_keywords = major_keywords + condition_keywords

        # Capitalize all SQL keywords
        for keyword in all_keywords:
            text = re.sub(rf'\b{keyword}\b', keyword, text, flags=re.IGNORECASE)

        # Split into statements (for handling multiple queries)
        statements = text.split(';')
        formatted_statements = []

        for statement in statements:
            if not statement.strip():
                continue

            # Add newlines and indentation
            lines = []
            indent_level = 0

            # Split on major keywords
            parts = re.split(r'\b(' + '|'.join(all_keywords) + r')\b', statement)
            for i, part in enumerate(parts):
                if not part.strip():
                    continue

                if part in major_keywords:
                    # Reset indent for major keywords
                    indent_level = 1
                    lines.append('\n' + part)
                elif part in condition_keywords:
                    # Indent conditions
                    lines.append('\n' + '    ' * indent_level + part)
                else:
                    # Handle the content after keywords
                    content = part.strip()
                    if i > 0 and parts[i-1] == 'SELECT':
                        # Format columns in SELECT clause
                        columns = [col.strip() for col in content.split(',')]
                        lines.append('\n    ' + ',\n    '.join(columns))
                    else:
                        # Format other content
                        lines.append(' ' + content)

            formatted_statements.append(''.join(lines).strip())

        # Join statements with semicolons
        result = ';\n\n'.join(formatted_statements)

        # Final cleanup
        result = re.sub(r'\s+\n', '\n', result)  # Remove trailing spaces
        result = re.sub(r'\n\s*\n', '\n', result)  # Remove empty lines

        return result
