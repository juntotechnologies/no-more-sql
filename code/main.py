import streamlit as st
from scripts import Scripts
from database import Database
import os

# Initialize database
db = Database()

# Create an instance of Scripts
faiss_handler = Scripts()

# Title of the app
st.title("No More SQL")
st.markdown("*Converts text to SQL code*")

# Initialize chat history
st.session_state.messages = st.session_state.get("messages", [])
st.session_state.current_interaction_id = st.session_state.get("current_interaction_id", None)

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# User input
if user_input := st.chat_input("What is your question?"):
    try:
        # Save user input to session state
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.write(user_input)

        # Get previous messages
        prev_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

        # Generate response
        with st.spinner("Generating response..."):
            assistant_message = faiss_handler.generate_response(user_input, prev_msgs)

        # Log the interaction to database
        interaction_id = db.log_interaction(user_input, assistant_message)
        st.session_state.current_interaction_id = interaction_id

        # Display the assistant's response
        with st.chat_message("assistant"):
            st.write(assistant_message)
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})

        # Display SQL with syntax highlighting
        st.code(assistant_message, language='sql')

        # Feedback section
        st.write("Did this SQL query work without modifications?")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Yes"):
                db.update_feedback(interaction_id, True)
                st.success("Thank you for your feedback!")

        with col2:
            if st.button("❌ No"):
                db.update_feedback(interaction_id, False)
                st.error("Thank you for your feedback!")

        # Optional feedback text
        feedback = st.text_area("Query that worked (optional):")
        if feedback:
            db.update_feedback(interaction_id, None, feedback)

        # Display statistics
        stats = db.get_statistics()
        if stats:
            total, success, failure = stats
            if total > 0:
                success_rate = (success / total) * 100
                st.info(f"Success rate: {success_rate:.1f}% ({success}/{total} queries worked first try)")

    except Exception as e:
        st.error(f"An error occurred: {e}")

    print("Response generation complete.")
