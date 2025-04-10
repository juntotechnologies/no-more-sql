import logging
import pandas as pd
from faiss_indexing_retrieval import FAISSIndex
import ollama
import re
import os
import random
import subprocess
import json
from collections import Counter

from dotenv import load_dotenv


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Ollama container endpoints
OLLAMA_ENDPOINTS = [
    "http://localhost:11434",  # ollama-gpu0
    "http://localhost:11435",  # ollama-gpu1
    "http://localhost:11436",  # ollama-gpu2
    "http://localhost:11437",  # ollama-gpu3
    "http://localhost:11438",  # ollama-gpu4
    "http://localhost:11439",  # ollama-gpu5
]

def get_available_models():
    """Dynamically discover models available in the Ollama containers"""
    logger.info("Discovering available models from Ollama containers")
    models = []

    for i in range(6):  # Assuming containers 0-5
        try:
            result = subprocess.run(
                ['docker', 'exec', f'ollama-gpu{i}', 'ollama', 'list'],
                capture_output=True, text=True, check=True
            )

            if result.stdout.strip():
                # Parse the text output
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and not line.startswith('NAME'):
                        # First column is the model name
                        parts = line.split()
                        if parts:
                            model_name = parts[0]
                            models.append(model_name)
                            logger.info(f"Found model in ollama-gpu{i}: {model_name}")

        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get models from ollama-gpu{i}: {e}")

    # Count which models appear in how many containers
    model_counts = Counter(models)
    # Get unique models
    unique_models = list(model_counts.keys())

    if not unique_models:
        logger.warning("No models found in any container! Using fallback models list.")
        return ["llama3.3:70b", "llama3.2:1b", "deepseek-r1:1.5b"]

    # Sort by popularity (most common first) and then alphabetically
    sorted_models = sorted(unique_models, key=lambda m: (-model_counts[m], m))
    logger.info(f"Available models across all containers: {sorted_models}")
    return sorted_models

# Get available models dynamically
AVAILABLE_MODELS = get_available_models()

class Scripts:
    def __init__(self, model_name='sentence-transformers/all-MiniLM-L6-v2', dataframe=None, llm_model=None):
        logger.info("Initializing FAISS Index")
        self.faiss_index = FAISSIndex(model_name)

        # Set default LLM model if not provided
        self.llm_model = llm_model if llm_model else AVAILABLE_MODELS[0]
        logger.info(f"Using LLM model: {self.llm_model}")

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

    def set_llm_model(self, model_name):
        """Update the LLM model to use for queries"""
        # Refresh available models to ensure we have the latest
        current_models = get_available_models()

        if model_name in current_models:
            self.llm_model = model_name
            logger.info(f"Model updated to: {self.llm_model}")
            return True
        else:
            logger.error(f"Requested model {model_name} is not available in any container")
            # Fall back to first available model
            if current_models:
                self.llm_model = current_models[0]
                logger.warning(f"Falling back to available model: {self.llm_model}")
                return False
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
        logger.info(f"Using model: {self.llm_model}")
        logger.info(instruction)
        # Call the Ollama API
        try:
            # Select a random Ollama endpoint for load balancing
            endpoint = random.choice(OLLAMA_ENDPOINTS)
            logger.info(f"Using Ollama endpoint: {endpoint}")

            # Temporarily override Ollama base URL
            original_base_url = ollama.BASE_URL
            ollama.BASE_URL = endpoint

            response = ollama.chat(
                model=self.llm_model,
                messages=[{'role': 'user', 'content': instruction}],
                stream=True
            )
            stream = [chunk['message']['content'] for chunk in response]
            text = "".join(stream)

            # Restore original base URL
            ollama.BASE_URL = original_base_url

            # Post-process the text
            text = self.format_response(text)

            return text
        except Exception as e:
            logger.error(f"Error calling Ollama API at {endpoint}: {e}")
            logger.info("Trying a different endpoint")

            # Try another endpoint if the first one fails
            try:
                # Remove failed endpoint temporarily
                remaining_endpoints = [ep for ep in OLLAMA_ENDPOINTS if ep != endpoint]
                if remaining_endpoints:
                    endpoint = random.choice(remaining_endpoints)
                    logger.info(f"Retrying with Ollama endpoint: {endpoint}")

                    # Set new endpoint
                    ollama.BASE_URL = endpoint

                    response = ollama.chat(
                        model=self.llm_model,
                        messages=[{'role': 'user', 'content': instruction}],
                        stream=True
                    )
                    stream = [chunk['message']['content'] for chunk in response]
                    text = "".join(stream)

                    # Post-process the text
                    text = self.format_response(text)

                    return text
                else:
                    return "All Ollama endpoints are unavailable."
            except Exception as retry_error:
                logger.error(f"Error on retry with Ollama API: {retry_error}")
                return "Error generating response. All Ollama endpoints failed."

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

    def generate_commit_summary(self, weeks=1):
        """Generate a bulleted summary of commits from the past specified weeks."""
        logger.info(f"Generating commit summary for past {weeks} weeks")

        # Get git log command output
        try:
            from datetime import datetime, timedelta
            import subprocess

            # Calculate date for specified weeks ago
            since_date = (datetime.now() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')

            # Run git log command
            git_log = subprocess.check_output(
                ['git', 'log', f'--since={since_date}', '--pretty=format:%s'],
                universal_newlines=True
            )

            if not git_log.strip():
                return "No commits found in the specified time period."

            # Create the instruction for Ollama
            instruction = (
                "You are a technical writer. Based on the following git commit messages, "
                "create a concise bulleted summary of the main changes. Group related changes together. "
                f"Here are the commit messages:\n\n{git_log}"
            )

            # Select a random Ollama endpoint for load balancing
            endpoint = random.choice(OLLAMA_ENDPOINTS)
            logger.info(f"Using Ollama endpoint: {endpoint}")

            # Temporarily override Ollama base URL
            original_base_url = ollama.BASE_URL
            ollama.BASE_URL = endpoint

            # Call the Ollama API
            try:
                response = ollama.chat(
                    model=self.llm_model,
                    messages=[{'role': 'user', 'content': instruction}],
                    stream=True
                )

                stream = [chunk['message']['content'] for chunk in response]
                summary = "".join(stream)

                # Restore original base URL
                ollama.BASE_URL = original_base_url

                return summary.strip()

            except Exception as e:
                logger.error(f"Error calling Ollama API at {endpoint}: {e}")
                logger.info("Trying a different endpoint")

                # Try another endpoint if the first one fails
                try:
                    # Remove failed endpoint temporarily
                    remaining_endpoints = [ep for ep in OLLAMA_ENDPOINTS if ep != endpoint]
                    if remaining_endpoints:
                        endpoint = random.choice(remaining_endpoints)
                        logger.info(f"Retrying with Ollama endpoint: {endpoint}")

                        # Set new endpoint
                        ollama.BASE_URL = endpoint

                        response = ollama.chat(
                            model=self.llm_model,
                            messages=[{'role': 'user', 'content': instruction}],
                            stream=True
                        )
                        stream = [chunk['message']['content'] for chunk in response]
                        summary = "".join(stream)

                        return summary.strip()
                    else:
                        return "All Ollama endpoints are unavailable."
                except Exception as retry_error:
                    logger.error(f"Error on retry with Ollama API: {retry_error}")
                    return "Error generating summary. All Ollama endpoints failed."

        except subprocess.CalledProcessError as e:
            logger.error(f"Error accessing git history: {e}")
            return "Error accessing git history."
        except Exception as e:
            logger.error(f"Error generating commit summary: {e}")
            return "Error generating summary."
