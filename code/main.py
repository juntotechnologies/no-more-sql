import streamlit as st
from scripts import Scripts  # Import the Scripts class

# Create an instance of Scripts
faiss_handler = Scripts()

# Title of the app
st.title("No More SQL")
st.markdown("*Converts text to SQL codes*")

# Initialize chat history
st.session_state.messages = st.session_state.get("messages", [])

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if user_input := st.chat_input("What is your question?"):
    try:
        # Save user input to session state
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        # Get previous messages
        prev_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

        # Display a loading spinner while generating a response
        with st.spinner("Generating response..."):
            # Generate response using the Scripts instance
            assistant_message = faiss_handler.generate_response(user_input, prev_msgs, k=2)  # Adjust k as needed

        # Display the assistant's response
        with st.chat_message("assistant"):
            st.markdown(assistant_message)
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})

    except Exception as e:
        st.error(f"An error occurred: {e}")

    print("Response generation complete.")
