#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime

import streamlit as st
import pandas as pd
import requests  # For direct API calls
from dotenv import load_dotenv, set_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env')

# Custom API Configuration
CUSTOM_API_URL = "https://claude-opus-chatbot.onrender.com/chat"

# Page configuration
st.set_page_config(
    page_title="𝚑𝚊𝚌𝚔🅶🅿🆃",
    page_icon="https://raw.githubusercontent.com/NoDataFound/hackGPT/main/res/hackgpt_fav.png",
    layout="wide"
)

# Define the chat history data as a Pandas DataFrame
CSS = """
<style>
img {
    box-shadow: 0px 10px 15px rgba(0, 0, 0, 0.2);
}
</style>
"""
st.markdown(f'{CSS}', unsafe_allow_html=True)

st.sidebar.image('https://raw.githubusercontent.com/NoDataFound/hackGPT/main/res/hackGPT_logo.png', width=300)
github_logo = "https://raw.githubusercontent.com/NoDataFound/hackGPT/main/res/github.png"
hackGPT_repo = "https://github.com/NoDataFound/hackGPT"
st.sidebar.markdown(f"[![GitHub]({github_logo})]({hackGPT_repo} 'hackGPT repo')")

# Persona Setup
def get_persona_files():
    """Get list of persona files - creates directory if missing"""
    if not os.path.exists("personas"):
        os.makedirs("personas")
    return [f.split(".")[0] for f in os.listdir("personas") if f.endswith(".md")]

persona_files = get_persona_files()
selected_persona = st.sidebar.selectbox("👤 𝖲𝖾𝗅𝖾𝖼𝗍 𝖫𝗈𝖼𝖺𝗅 𝖯𝖾𝗋𝗌𝗈𝗇𝖺", ["None"] + persona_files)

# Model setup (for display only - API doesn't use this)
MODEL = st.sidebar.selectbox(
    label='Model',
    options=[
        'claude-opus',
        'gpt-3.5-turbo',
        'gpt-4',
        'text-davinci-003'
    ]
)

default_temperature = 1.0
temperature = st.sidebar.slider(
    "𝗧𝗲𝗺𝗽𝗲𝗿𝗮𝘁𝘂𝗿𝗲 | 𝗖𝗿𝗲𝗮𝘁𝗶𝘃𝗲 <𝟬.𝟱",
    min_value=0.0,
    max_value=1.0,
    step=0.1,
    value=default_temperature
)
max_tokens = st.sidebar.slider("𝗠𝗔𝗫 𝗢𝗨𝗧𝗣𝗨𝗧 𝗧𝗢𝗞𝗘𝗡𝗦", 10, 4000, 2300)

# Prompt Setups
url = "https://raw.githubusercontent.com/f/awesome-chatgpt-prompts/main/prompts.csv"
jailbreaks = "https://raw.githubusercontent.com/NoDataFound/hackGPT/main/jailbreaks.csv"

try:
    data = pd.read_csv(url)
    new_row = pd.DataFrame({"act": [" "], "prompt": [""]})
    data = pd.concat([data, new_row], ignore_index=True)
except Exception as e:
    logger.error(f"Failed to load remote personas: {e}")
    data = pd.DataFrame({"act": [" "], "prompt": [""]})

try:
    jailbreakdata = pd.read_csv(jailbreaks)
    jailbreaknew_row = pd.DataFrame({"hacker": [" "], "text": [""]})
    jailbreakdata = pd.concat([jailbreakdata, jailbreaknew_row], ignore_index=True)
except Exception as e:
    logger.error(f"Failed to load jailbreaks: {e}")
    jailbreakdata = pd.DataFrame({"hacker": [" "], "text": [""]})

expand_section = st.sidebar.expander("👤 Manage Personas", expanded=False)

with expand_section:
    if selected_persona and selected_persona != "None":
        persona_path = os.path.join("personas", f"{selected_persona}.md")
        if os.path.exists(persona_path):
            with open(persona_path, "r") as f:
                persona_text = f.read()
            
            new_persona_name = st.text_input("Persona Name:", value=selected_persona)
            new_persona_prompt = st.text_area("Persona Prompt:", value=persona_text, height=100)
            
            if new_persona_name != selected_persona or new_persona_prompt != persona_text:
                with open(os.path.join("personas", f"{new_persona_name}.md"), "w") as f:
                    f.write(new_persona_prompt)
                if new_persona_name != selected_persona:
                    os.remove(persona_path)
                    persona_files.remove(selected_persona)
                    persona_files.append(new_persona_name)
                    selected_persona = new_persona_name
            
            if st.button("➖ Delete Persona"):
                os.remove(persona_path)
                persona_files.remove(selected_persona)
                selected_persona = "None"
                st.warning("Persona Deleted")

expand_section = st.sidebar.expander("🥷 Import Remote Persona", expanded=False)

with expand_section:
    selected_act = st.selectbox('', data['act'])
    show_remote_prompts = st.checkbox("Show remote prompt options")
    if selected_act and selected_act.strip():
        selected_prompt = data.loc[data['act'] == selected_act, 'prompt'].values[0]
        confirm = st.button("Save Selected Persona")
        if confirm:
            if not os.path.exists("personas"):
                os.mkdir("personas")
            with open(os.path.join("personas", f"{selected_act}_remote.md"), "w") as f:
                f.write(selected_prompt)
            st.success(f"Persona '{selected_act}' saved!")

expand_section = st.sidebar.expander("🏴‍☠️ Jailbreaks", expanded=False)

with expand_section:
    selected_hacker = st.selectbox('', jailbreakdata['hacker'])
    show_hack_prompts = st.checkbox("Show jailbreak options")
    if selected_hacker and selected_hacker.strip():
        selected_jailbreak_prompt = jailbreakdata.loc[jailbreakdata['hacker'] == selected_hacker, 'text'].values[0]
        confirm = st.button("Save Selected Jailbreak")
        if confirm:
            if not os.path.exists("personas"):
                os.mkdir("personas")
            with open(os.path.join("personas", f"{selected_hacker}_jailbreak.md"), "w") as f:
                f.write(selected_jailbreak_prompt)
            st.success(f"Jailbreak '{selected_hacker}' saved!")

expand_section = st.sidebar.expander("➕ Add new Persona", expanded=False)

if show_hack_prompts:
    st.write(jailbreakdata[['hacker', 'text']].style.hide(axis="index").set_properties(
        subset='text',
        **{'max-width': '100%', 'white-space': 'pre-wrap'}
    ))
elif show_remote_prompts:
    st.write(data[['act', 'prompt']].style.hide(axis="index").set_properties(
        subset='prompt',
        **{'max-width': '100%', 'white-space': 'pre-wrap'}
    ))

with expand_section:
    st.subheader("➕ Add new Persona")
    st.text("Press enter to update/save")
    persona_files = get_persona_files()
    new_persona_name = st.text_input("Persona Name:")
    if new_persona_name in persona_files:
        st.error("This persona name already exists. Please choose a different name.")
    else:
        new_persona_prompt = st.text_area("Persona Prompt:", height=100)
        if new_persona_name and new_persona_prompt:
            with open(os.path.join("personas", f"{new_persona_name}.md"), "w") as f:
                f.write(new_persona_prompt)
            persona_files.append(new_persona_name)
            selected_persona = new_persona_name
            st.success(f"Persona '{new_persona_name}' created!")

# Load persona text
persona_text = ""
if selected_persona and selected_persona != "None":
    persona_path = os.path.join("personas", f"{selected_persona}.md")
    if os.path.exists(persona_path):
        with open(persona_path, "r") as f:
            persona_text = f.read()

# Define the function to get the AI's response using CUSTOM API
def get_ai_response(text_input):
    """Get AI response using custom Claude API"""
    try:
        # Combine persona with user input
        final_message = text_input
        if persona_text:
            final_message = f"{persona_text}\n\nUser: {text_input}"
        
        # Make POST request to custom API
        response = requests.post(
            CUSTOM_API_URL,
            json={
                "message": final_message,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            # Extract response - adjust based on actual API response format
            if isinstance(result, dict):
                return result.get('response', result.get('message', result.get('text', str(result))))
            return str(result)
        else:
            return f"Error: API returned status {response.status_code}"
    
    except Exception as e:
        logger.error(f"Error in get_ai_response: {e}")
        return f"Error: {str(e)}"

try:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if len(st.session_state.chat_history) == 0:
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Persona", selected_persona, selected_persona)
        col2.metric("Persona Count", len(persona_files), len(persona_files))
        col3.metric("Jailbreaks", len(jailbreakdata), len(jailbreakdata))
        col4.metric("Model", MODEL)
        col5.metric("Model Count", len(MODEL), len(MODEL))
    else:
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Persona", selected_persona, selected_persona)
        col2.metric("Persona Count", len(persona_files), len(persona_files))
        col3.metric("Jailbreaks", len(jailbreakdata), len(jailbreakdata))
        col4.metric("Model", MODEL)
        col5.metric("Model Count", len(MODEL), len(MODEL))
        col6.metric("Messages", len(st.session_state.chat_history), len(st.session_state.chat_history))
except Exception as e:
    logger.error(f"Error displaying metrics: {e}")

file = st.sidebar.file_uploader("📁 Upload Text File", type=["txt"])

user_css = """
<style>
.user {
    display: inline-block;
    padding: 8px;
    border-radius: 10px;
    margin-bottom: 1px;
    border: 1px solid #e90ce4;
    width: 100%;
    height: 100%;
    overflow-y: scroll;
}
</style>
"""

ai_css = """
<style>
.ai {
    display: inline-block;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 1px;
    border: 1px solid #0ab5e0;
    width: 100%;
    overflow-x: scroll;
    height: 100%;
    overflow-y: scroll;
}
</style>
"""

model_css = """
<style>
.model {
    display: inline-block;
    background-color: #f0e0ff;
    padding: 1px;
    border-radius: 5px;
    margin-bottom: 5px;
    width: 100%;
    height: 100%;
    overflow-y: scroll;
}
</style>
"""

st.markdown(user_css, unsafe_allow_html=True)
st.markdown(ai_css, unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def display_chat_history():
    """Display chat history with custom styling"""
    for i, (role, text) in reversed(list(enumerate(st.session_state.chat_history))):
        alignment = 'left' if role == 'user' else 'left'
        
        if role == 'user':
            margin = 'margin-bottom: 1px;'
        else:
            margin = 'margin-top: 8px;'
        
        col1, col2 = st.columns([2, 8])
        with col1:
            if role == 'user':
                st.markdown(f'<div style="{margin}" class="{role}">{text}</div>', unsafe_allow_html=True)
            if role == 'model':
                st.markdown(f'<div style="text-align: left; color: green;" class="{role}">{text}</div>', unsafe_allow_html=True)
            else:
                st.markdown('')
        with col2:
            if role == 'ai':
                st.markdown(f'<div style="text-align: {alignment}; {margin}" class="{role}">{text}</div>', unsafe_allow_html=True)
            if role == 'persona':
                st.markdown(f'<div style="text-align: right; color: orange;" class="{role}">{text}</div>', unsafe_allow_html=True)

st.write("")
text_input = st.text_input(
    "",
    value="",
    key="text_input",
    placeholder="Type your message here...",
    help="Press Enter to send your message."
)

if text_input:
    ai_response = get_ai_response(text_input)
    st.session_state.chat_history.append(('ai', f"{ai_response}"))
    st.session_state.chat_history.append(('persona', f"{selected_persona}"))
    st.session_state.chat_history.append(('user', f"You: {text_input}"))
    st.session_state.chat_history.append(('model', f"{MODEL}"))

display_chat_history()

# File upload processing
if file is not None:
    text = file.read().decode("utf-8")
    st.write(f"Input: {text}")
    response = get_ai_response(text)
    st.write(f"Output: {response}")

if st.button("Download Chat History"):
    chat_history_text = "\n".join([text for _, text in st.session_state.chat_history])
    st.download_button(
        label="Download Chat History",
        data=chat_history_text.encode(),
        file_name="chat_history.txt",
        mime="text/plain",
    )
