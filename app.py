# ------------------QNA BOT WITH GROQ AND GOOGLE SEARCH TOOL-----------------
# Fully functional QNA bot that can answer questions using Groq LLM and Google Search Tool. It also has memory to save the conversation history and streaming to stream the response from the agent. The bot is deployed on Streamlit for a web interface.

# LLM--Groq
# Tool-Google Search Tool
# Agent
# Memory
# Streaming
# Streamlit --Web Interface-UI
# Firebase -- Authentication and Database to save chats and messages


from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
from langchain_community.utilities import GoogleSerperAPIWrapper # Google Search API Wrapper
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver # To save the conversation history in memory
import streamlit as st

import pyrebase
import uuid
import time

st.set_page_config(
    page_title="Samvaad AI - Your Personal ChatGPT",
    page_icon="🤖",
    layout="wide"
)

#  Firebase Config
import os

firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL")
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()



# Auth Functions (ADD HERE)
def signup(email, password):
    try:
        user = auth.create_user_with_email_and_password(email, password)
        return user
    except Exception as e:
        print(e)   
        return None


def login(email, password):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        return user
    except Exception as e: 
        print(e)         
        return None
# ---------------- SESSION THREAD ----------------   
thread_id = st.session_state.get("user_id", "guest")

# ---------------- CHAT FUNCTIONS ----------------

def create_new_chat():

    chat_id = str(uuid.uuid4())

    db.child("users").child(thread_id).child("chats").child(chat_id).set({
        "title": "New Chat",
        "created_at": time.time()
    })

    st.session_state.chat_id = chat_id
    st.session_state.history = []


def load_chat(chat_id):

    st.session_state.history = []

    messages = db.child("users") \
        .child(thread_id) \
        .child("chats") \
        .child(chat_id) \
        .child("messages") \
        .get()

    if messages and messages.each():

        for msg in messages.each():

            data = msg.val()

            st.session_state.history.append({
                "role": data["role"],
                "content": data["message"]
            })


# Sidebar Authentication UI
st.sidebar.title("🔐 Authentication")

# if logged in  → then show Logout button and Chats
# ---------------- IF USER LOGGED IN ----------------

if "user_id" in st.session_state:

    name = st.session_state.get("name", "User")

    st.sidebar.success(f"Welcome {name} 🎉")

    # Logout
    if st.sidebar.button("Logout"):

        st.session_state.clear()
        st.rerun()

    # ---------------- CHAT SIDEBAR ----------------

    st.sidebar.markdown("---")
    st.sidebar.subheader("💬 Chats")

    # ➕ New Chat
    if st.sidebar.button("➕ New Chat"):

        create_new_chat()
        st.rerun()

    # Load Chats
    chats = db.child("users").child(thread_id).child("chats").get()

    if chats and chats.each():

        for chat in chats.each():

            chat_id = chat.key()

            title = chat.val().get("title", "Chat")

            col1, col2 = st.sidebar.columns([4, 1])

            # Open Chat
            if col1.button(title, key=chat_id):

                st.session_state.chat_id = chat_id

                load_chat(chat_id)

                st.rerun()

            # Delete Chat
            if col2.button("🗑️", key=f"delete_{chat_id}"):

                db.child("users") \
                    .child(thread_id) \
                    .child("chats") \
                    .child(chat_id) \
                    .remove()

                st.rerun()


# ❌ if not logged in → then show Login/Signup options
else:
    
    choice = st.sidebar.selectbox("Choose", ["Login", "Signup"])

    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    # Signup
    name = ""
    if choice == "Signup":
        name = st.sidebar.text_input("Name")
        if st.sidebar.button("Create Account"):

            if not email or not password:
                st.sidebar.error("Please fill all fields ❌")
            else:
                user = signup(email.strip(), password.strip())

                if user:
                    st.session_state.name = name 
                    st.sidebar.success("Account created successfully ✅")
                else:
                    st.sidebar.error("Signup failed or User Exists ❌")

    # Login
    if choice == "Login":
        if st.sidebar.button("Login"):

            if not email or not password:
                st.sidebar.error("Please fill all fields ❌")
            else:
                user = login(email.strip(), password.strip())

                if user:
                    st.session_state.user = user
                    st.session_state.user_id = user["localId"]
                    st.session_state.name = email.split("@")[0]

                    st.session_state.memory = InMemorySaver()
                    st.session_state.history = []
                    st.session_state.chat_id = None

                    st.rerun()   
                else:
                    st.sidebar.error("Invalid email or password ❌")
                

# 🔐 Protect chatbot (ADD THIS)
if "user_id" not in st.session_state:
    st.warning("Please login to use Samvaad AI 🔐")
    st.stop()
    
# ---------------- AUTO CREATE FIRST CHAT ----------------

if "chat_id" not in st.session_state or st.session_state.chat_id is None:
    create_new_chat()


llm=ChatGroq(model="openai/gpt-oss-20b",streaming=True)

search=GoogleSerperAPIWrapper() # Initialize the Google Search API Wrapper
tool=[search.run] # Define the tools to be used by the agent
# memory=InMemorySaver() # Initialize the InMemorySaver to save the conversation history in memory



# ---------------- MEMORY ----------------

if "memory" not in st.session_state:

    st.session_state.memory = InMemorySaver()

if "history" not in st.session_state:

    st.session_state.history = []


# ---------------- AGENT ----------------
agent=create_agent(
    model=llm,  
    tools=tool,
    system_prompt="You are a Agent and you can search any question on google.",
    checkpointer=st.session_state.memory # Pass the memory object to the agent to save the conversation history
)

# print(st.session_state.memory) #for showing address of memory

# Building Web Interface using Streamlit

st.markdown(
    "<h2 style='text-align:center; color:#4B0082;'>⚡Samvaad AI - Answer at the speed of thought</h2>",
    unsafe_allow_html=True
)


for message in st.session_state.history:
    role=message["role"]
    content=message["content"]
    st.chat_message(role).markdown(content)

query=st.chat_input("Ask me anything...")

if query:

    # User Message UI
    st.chat_message("user").markdown(query)

    # Save to Session
    st.session_state.history.append({
        "role": "user",
        "content": query
    })

    # ---------------- AUTO TITLE ----------------

    if len(st.session_state.history) == 1:

        title = query[:30]

        db.child("users") \
            .child(thread_id) \
            .child("chats") \
            .child(st.session_state.chat_id) \
            .update({
                "title": title
            })

    # ---------------- SAVE USER MESSAGE ----------------

    db.child("users") \
        .child(thread_id) \
        .child("chats") \
        .child(st.session_state.chat_id) \
        .child("messages") \
        .push({
            "role": "user",
            "message": query
        })


    response=agent.stream(
        {"messages":[{"role":"user","content":query}]},
        {"configurable":{"thread_id":thread_id}} ,# Pass the thread_id to the agent to save the conversation history in memory       
        stream_mode="messages" #streaming chunks
    )

    ai_container = st.chat_message("assistant")

    with ai_container:
        space = st.empty()
        message = ""

        with st.spinner("Thinking..."):
            for chunk in response:
                if chunk and chunk[0].content:
                    message += chunk[0].content
                    space.markdown(message + "▌")   # typing effect

        space.markdown(message)  # final clean text

    
    # ---------------- SAVE ASSISTANT MESSAGE ----------------

    st.session_state.history.append({
        "role": "assistant",
        "content": message
    })

    db.child("users") \
        .child(thread_id) \
        .child("chats") \
        .child(st.session_state.chat_id) \
        .child("messages") \
        .push({
            "role": "assistant",
            "message": message
        })

    # answer=response['messages'][-1].content
    # st.chat_message("AI").markdown(answer)