import streamlit as st
from scripts import Scripts  # Import the Scripts class

# Create an instance of Scripts
faiss_handler = Scripts()

# Title of the app
st.title("No More SQL")
st.markdown("*Converts text to SQL code*")

# Initialize chat history
st.session_state.messages = st.session_state.get("messages", [])

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])  # Changed to st.write()

# User input
if user_input := st.chat_input("What is your question?"):
    try:
        # Save user input to session state
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.write(user_input)  # Changed to st.write()

        # Get previous messages
        prev_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

        # Display a loading spinner while generating a response
        with st.spinner("Generating response..."):
            # Generate response using the Scripts instance
            assistant_message = faiss_handler.generate_response(user_input, prev_msgs)  # Adjust k as needed

        # Display the assistant's response
        with st.chat_message("assistant"):
            # Option 1: Using st.write()
            st.write(assistant_message)
            
            # Option 2: Using triple backticks
            # st.markdown(f"```\n{assistant_message}\n```")
            
            # Option 3: Using HTML (use cautiously)
            # st.markdown(f"<pre>{assistant_message}</pre>", unsafe_allow_html=True)
            
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})

    except Exception as e:
        st.error(f"An error occurred: {e}")

    print("Response generation complete.")