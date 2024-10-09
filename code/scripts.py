from faiss_indexing_retrieval import FAISSIndex
import ollama

class Scripts:
    def __init__(self, model_name='sentence-transformers/all-MiniLM-L6-v2'):
        print("Initialization")
        self.faiss_index = FAISSIndex(model_name)
        self.sentences = self.load_sentences()
        self.faiss_index.create_index(self.sentences)

    def load_sentences(self):
        # Load your sentences from a file or database
        return ["Sample sentence 1.", "Sample sentence 2.", "Sample sentence 3."]  # Replace with actual loading logic

    def generate_response(self, user_input, prev_messages, k):
        print("Generate Responses")
        # Retrieve context from the FAISS index
        context = self.faiss_index.retrieve_top_k(user_input, k=k)
        
        # Format previous messages
        formatted_prev_msgs = "\n".join(f"{msg['role']}: {msg['content']}" for msg in prev_messages)
        
        # Create the instruction for Ollama
        instruction = (
            "You are an expert at writing SQL codes. Based on the user query, "
            f"write the SQL code. ### input: {user_input} ### context: {context} ### previous messages: {formatted_prev_msgs} ### output:"
        )
        print("Calling Ollama")
        # Call the Ollama API
        response = ollama.chat(model='llama3.1:8b', messages=[{'role': 'user', 'content': instruction}])
        
        return response['message']['content']
