import streamlit as st
from scripts import Scripts, AVAILABLE_MODELS, get_available_models
from database import Database
import pandas as pd
import os
from datetime import datetime, timedelta

# Initialize database
db = Database()

# Setup model refresh functionality
if 'last_model_refresh' not in st.session_state:
    st.session_state.last_model_refresh = datetime.now()
    st.session_state.available_models = AVAILABLE_MODELS

# Check if we need to refresh models (every 5 minutes)
if datetime.now() - st.session_state.last_model_refresh > timedelta(minutes=5):
    st.session_state.available_models = get_available_models()
    st.session_state.last_model_refresh = datetime.now()

# Load the combined CSV file
combined_csv_path = os.path.join('data', 'combined_prompts_queries.csv')
df = pd.read_csv(combined_csv_path)

# Extract unique sources
sources = df['Source'].unique()

# Create sidebar for settings
st.sidebar.title("Settings")

# Debug option
debug_mode = st.sidebar.checkbox("Debug Mode")

# Refresh models button
if st.sidebar.button("🔄 Refresh Models"):
    # Create a placeholder for status in sidebar
    refresh_status = st.sidebar.empty()
    refresh_status.info("Refreshing models...")

    # Refresh models
    st.session_state.available_models = get_available_models()
    st.session_state.last_model_refresh = datetime.now()

    # Update status
    refresh_status.success("Models refreshed!")

# Show available models if in debug mode
if debug_mode:
    st.sidebar.markdown("### Debug Info")
    st.sidebar.markdown("##### Available Models")
    for model in st.session_state.available_models:
        st.sidebar.markdown(f"- {model}")

# Model selection in sidebar
selected_model = st.sidebar.selectbox(
    "Select LLM Model:",
    st.session_state.available_models,
    index=0 if not st.session_state.get('current_model') else
          max(0, st.session_state.available_models.index(st.session_state.current_model)
              if st.session_state.current_model in st.session_state.available_models else 0)
)

# Source selection in sidebar
selected_source = st.sidebar.selectbox(
    "Select Source for SQL prompts:",
    sources,
    index=0  # Default to first source
)

# Filter data by selected source
filtered_df = df[df['Source'] == selected_source]

# Create an instance of Scripts with filtered data and selected model
faiss_handler = Scripts(dataframe=filtered_df, llm_model=selected_model)

# Save model in session state to detect changes
if 'current_model' not in st.session_state:
    st.session_state.current_model = selected_model
elif st.session_state.current_model != selected_model:
    # Model has changed, update the handler
    faiss_handler.set_llm_model(selected_model)
    st.session_state.current_model = selected_model

# Title of the app
st.title("No More SQL")
st.markdown("*Converts text to SQL code*")

# Model info display
st.info(f"Using model: **{selected_model}**")

# Show model availability across containers
if st.checkbox("Show model availability details"):
    with st.expander("Model availability across containers"):
        st.markdown("##### Model availability across containers")
        availability_data = []
        for i in range(6):
            try:
                result = os.popen(f"docker exec ollama-gpu{i} ollama list 2>/dev/null || echo 'Container not running'").read()
                if "not running" not in result:
                    models = []
                    for line in result.strip().split('\n'):
                        parts = line.split()
                        if parts and not parts[0].startswith('NAME'):
                            models.append(parts[0])
                    availability_data.append((f"GPU {i}", ", ".join(models)))
                else:
                    availability_data.append((f"GPU {i}", "Container not running"))
            except Exception as e:
                availability_data.append((f"GPU {i}", f"Error: {str(e)}"))

        # Display as a table
        st.table(pd.DataFrame(availability_data, columns=["Container", "Available Models"]))

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
