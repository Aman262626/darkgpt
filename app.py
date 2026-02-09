#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DarkGPT v3.0 - Modern AI Chat Interface
Secure, Production-Ready, Modular Architecture
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('darkgpt.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
MAX_HISTORY_MESSAGES = 50
MAX_MESSAGE_LENGTH = 4000
MAX_TOKENS = 4096
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 2

# Rate limiting: max requests per user per minute
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60  # seconds


class SecurityManager:
    """Handle input validation and security checks"""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Remove potentially harmful characters"""
        if not text:
            return ""
        # Remove null bytes and control characters
        text = text.replace('\x00', '').strip()
        # Limit length
        if len(text) > MAX_MESSAGE_LENGTH:
            text = text[:MAX_MESSAGE_LENGTH]
        return text
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate OpenAI API key format"""
        if not api_key:
            return False
        # OpenAI keys start with 'sk-' and are typically 51 chars
        return api_key.startswith('sk-') and len(api_key) >= 40
    
    @staticmethod
    def get_user_id() -> str:
        """Generate anonymous user ID for rate limiting"""
        # Use session state or generate from timestamp
        if 'user_id' not in st.session_state:
            st.session_state.user_id = hashlib.md5(
                str(time.time()).encode()
            ).hexdigest()[:16]
        return st.session_state.user_id


class RateLimiter:
    """Simple rate limiting to prevent API abuse"""
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    def check_rate_limit(self, user_id: str) -> Tuple[bool, int]:
        """Check if user exceeded rate limit"""
        now = time.time()
        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < RATE_LIMIT_WINDOW
        ]
        
        if len(self.requests[user_id]) >= RATE_LIMIT_REQUESTS:
            # Calculate wait time
            oldest_request = min(self.requests[user_id])
            wait_time = int(RATE_LIMIT_WINDOW - (now - oldest_request))
            return False, wait_time
        
        self.requests[user_id].append(now)
        return True, 0


class OpenAIClient:
    """Modern OpenAI API client with error handling and retries"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = MAX_TOKENS
    ) -> Optional[str]:
        """Send chat completion request with retries"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=REQUEST_TIMEOUT
                )
                return response.choices[0].message.content
            
            except OpenAIError as e:
                logger.error(f"OpenAI API error (attempt {attempt + 1}): {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                else:
                    return None
            
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return None
        
        return None


class PersonaManager:
    """Manage persona files and prompts"""
    
    def __init__(self, personas_dir: str = "personas"):
        self.personas_dir = Path(personas_dir)
        self.personas_dir.mkdir(exist_ok=True)
    
    def get_persona_files(self) -> List[str]:
        """Get list of available personas"""
        return sorted([
            f.stem for f in self.personas_dir.glob("*.md")
        ])
    
    def load_persona(self, persona_name: str) -> Optional[str]:
        """Load persona prompt from file"""
        if not persona_name:
            return None
        
        file_path = self.personas_dir / f"{persona_name}.md"
        if not file_path.exists():
            return None
        
        try:
            return file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error loading persona {persona_name}: {str(e)}")
            return None
    
    def save_persona(self, persona_name: str, prompt: str) -> bool:
        """Save persona prompt to file"""
        if not persona_name or not prompt:
            return False
        
        # Sanitize filename
        safe_name = "".join(c for c in persona_name if c.isalnum() or c in (' ', '_', '-')).strip()
        if not safe_name:
            return False
        
        file_path = self.personas_dir / f"{safe_name}.md"
        try:
            file_path.write_text(prompt, encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"Error saving persona {safe_name}: {str(e)}")
            return False
    
    def delete_persona(self, persona_name: str) -> bool:
        """Delete persona file"""
        file_path = self.personas_dir / f"{persona_name}.md"
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Error deleting persona {persona_name}: {str(e)}")
            return False


class ChatManager:
    """Manage chat history and messages"""
    
    @staticmethod
    def initialize_session():
        """Initialize session state variables"""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'message_count' not in st.session_state:
            st.session_state.message_count = 0
    
    @staticmethod
    def add_message(role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to chat history"""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        st.session_state.chat_history.append(message)
        st.session_state.message_count += 1
        
        # Limit history size
        if len(st.session_state.chat_history) > MAX_HISTORY_MESSAGES:
            st.session_state.chat_history = st.session_state.chat_history[-MAX_HISTORY_MESSAGES:]
    
    @staticmethod
    def get_messages_for_api() -> List[Dict[str, str]]:
        """Get formatted messages for OpenAI API"""
        return [
            {'role': msg['role'], 'content': msg['content']}
            for msg in st.session_state.chat_history
            if msg['role'] in ('user', 'assistant', 'system')
        ]
    
    @staticmethod
    def clear_history():
        """Clear chat history"""
        st.session_state.chat_history = []
        st.session_state.message_count = 0
    
    @staticmethod
    def export_history() -> str:
        """Export chat history as text"""
        lines = []
        for msg in st.session_state.chat_history:
            timestamp = msg.get('timestamp', '')
            role = msg.get('role', '').upper()
            content = msg.get('content', '')
            lines.append(f"[{timestamp}] {role}: {content}\n")
        return "\n".join(lines)


def setup_page():
    """Configure Streamlit page"""
    st.set_page_config(
        page_title="DarkGPT v3.0",
        page_icon="🌑",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .user-message {
            background-color: #1e1e2e;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 3px solid #e90ce4;
        }
        .assistant-message {
            background-color: #16213e;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 3px solid #0ab5e0;
        }
        .system-message {
            background-color: #1a1a2e;
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
            font-size: 0.9em;
            color: #888;
        }
        </style>
    """, unsafe_allow_html=True)


def render_sidebar(persona_manager: PersonaManager) -> Dict:
    """Render sidebar with settings and persona management"""
    st.sidebar.title("🌑 DarkGPT v3.0")
    st.sidebar.markdown("**Modern AI Chat Interface**")
    st.sidebar.markdown("---")
    
    # API Key Configuration
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or not SecurityManager.validate_api_key(api_key):
        st.sidebar.warning("⚠️ OpenAI API key not configured")
        api_key = st.sidebar.text_input(
            "Enter OpenAI API Key",
            type="password",
            help="Get your API key from https://platform.openai.com/api-keys"
        )
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
    
    # Model Selection
    model = st.sidebar.selectbox(
        "🤖 Model",
        options=[
            'gpt-3.5-turbo',
            'gpt-3.5-turbo-16k',
            'gpt-4',
            'gpt-4-turbo-preview'
        ],
        index=0
    )
    
    # Parameters
    temperature = st.sidebar.slider(
        "🌡️ Temperature",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1,
        help="Higher values = more creative, Lower values = more focused"
    )
    
    max_tokens = st.sidebar.slider(
        "📏 Max Tokens",
        min_value=100,
        max_value=4096,
        value=2048,
        step=100
    )
    
    st.sidebar.markdown("---")
    
    # Persona Management
    st.sidebar.subheader("👤 Persona")
    personas = persona_manager.get_persona_files()
    selected_persona = st.sidebar.selectbox(
        "Select Persona",
        options=["None"] + personas,
        index=0
    )
    
    persona_prompt = None
    if selected_persona != "None":
        persona_prompt = persona_manager.load_persona(selected_persona)
        if persona_prompt:
            with st.sidebar.expander("📝 Edit Persona", expanded=False):
                edited_prompt = st.text_area(
                    "Persona Prompt",
                    value=persona_prompt,
                    height=150
                )
                if st.button("💾 Save Changes"):
                    if persona_manager.save_persona(selected_persona, edited_prompt):
                        st.success("✅ Persona updated!")
                        st.rerun()
                
                if st.button("🗑️ Delete Persona"):
                    if persona_manager.delete_persona(selected_persona):
                        st.success("✅ Persona deleted!")
                        st.rerun()
    
    # Add New Persona
    with st.sidebar.expander("➕ Create New Persona", expanded=False):
        new_name = st.text_input("Persona Name")
        new_prompt = st.text_area("Persona Prompt", height=100)
        if st.button("💾 Create Persona"):
            if new_name and new_prompt:
                if persona_manager.save_persona(new_name, new_prompt):
                    st.success(f"✅ Persona '{new_name}' created!")
                    st.rerun()
            else:
                st.error("❌ Name and prompt required")
    
    st.sidebar.markdown("---")
    
    # Actions
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            ChatManager.clear_history()
            st.rerun()
    
    with col2:
        if st.button("💾 Export", use_container_width=True):
            export_text = ChatManager.export_history()
            st.download_button(
                label="📥 Download",
                data=export_text,
                file_name=f"darkgpt_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    # Stats
    st.sidebar.markdown("---")
    st.sidebar.metric("💬 Messages", st.session_state.get('message_count', 0))
    st.sidebar.metric("👤 Personas", len(personas))
    
    return {
        'api_key': api_key,
        'model': model,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'persona_prompt': persona_prompt,
        'selected_persona': selected_persona
    }


def render_chat_message(message: Dict):
    """Render a single chat message"""
    role = message.get('role', '')
    content = message.get('content', '')
    
    if role == 'user':
        st.markdown(
            f'<div class="user-message">👤 <b>You:</b><br>{content}</div>',
            unsafe_allow_html=True
        )
    elif role == 'assistant':
        st.markdown(
            f'<div class="assistant-message">🤖 <b>DarkGPT:</b><br>{content}</div>',
            unsafe_allow_html=True
        )
    elif role == 'system':
        st.markdown(
            f'<div class="system-message">ℹ️ {content}</div>',
            unsafe_allow_html=True
        )


def main():
    """Main application entry point"""
    setup_page()
    
    # Initialize managers
    persona_manager = PersonaManager()
    rate_limiter = RateLimiter()
    ChatManager.initialize_session()
    
    # Render sidebar and get settings
    settings = render_sidebar(persona_manager)
    
    # Main content area
    st.title("🌑 DarkGPT v3.0")
    st.markdown("**Secure, Modern AI Chat Interface**")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            render_chat_message(message)
    
    # Input area
    user_input = st.chat_input(
        "Type your message here...",
        key="user_input"
    )
    
    if user_input:
        # Security checks
        user_input = SecurityManager.sanitize_input(user_input)
        if not user_input:
            st.error("❌ Invalid input")
            return
        
        # Rate limiting
        user_id = SecurityManager.get_user_id()
        allowed, wait_time = rate_limiter.check_rate_limit(user_id)
        if not allowed:
            st.warning(f"⏱️ Rate limit exceeded. Please wait {wait_time} seconds.")
            return
        
        # Check API key
        api_key = settings.get('api_key')
        if not api_key or not SecurityManager.validate_api_key(api_key):
            st.error("❌ Please configure a valid OpenAI API key in the sidebar")
            return
        
        # Add user message
        ChatManager.add_message('user', user_input)
        
        # Prepare messages for API
        messages = []
        
        # Add persona as system message if selected
        persona_prompt = settings.get('persona_prompt')
        if persona_prompt:
            messages.append({
                'role': 'system',
                'content': persona_prompt
            })
        
        # Add conversation history
        messages.extend(ChatManager.get_messages_for_api())
        
        # Show processing indicator
        with st.spinner("🤔 Thinking..."):
            try:
                # Create OpenAI client and get response
                client = OpenAIClient(api_key)
                response = client.chat_completion(
                    messages=messages,
                    model=settings.get('model', 'gpt-3.5-turbo'),
                    temperature=settings.get('temperature', 0.7),
                    max_tokens=settings.get('max_tokens', 2048)
                )
                
                if response:
                    # Add assistant response
                    ChatManager.add_message(
                        'assistant',
                        response,
                        metadata={
                            'model': settings.get('model'),
                            'persona': settings.get('selected_persona')
                        }
                    )
                    st.rerun()
                else:
                    st.error("❌ Failed to get response from API. Please try again.")
                    ChatManager.add_message(
                        'system',
                        'Error: Failed to get response from API'
                    )
            
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                st.error(f"❌ An error occurred: {str(e)}")
                ChatManager.add_message('system', f'Error: {str(e)}')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}", exc_info=True)
        st.error(f"❌ Critical error: {str(e)}")
        st.stop()
