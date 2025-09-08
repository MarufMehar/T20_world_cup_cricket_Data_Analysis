import streamlit as st
import fitz
from sentence_transformers import SentenceTransformer
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import ollama
import psycopg2

# ---------- DB ----------
conn = psycopg2.connect(
    dbname="vector_database",
    user="postgres",
    password="1202",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# ---------- User ID from query param ----------
query_params = st.experimental_get_query_params()
user_id = int(query_params.get("user_id", [1])[0])

# ---------- Load Sessions ----------
cur.execute("SELECT id, title FROM chat_sessions WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
sessions = cur.fetchall()
session_options = ["➕ New Chat"] + [f"{s[1]} (ID {s[0]})" for s in sessions]
selected = st.sidebar.selectbox("Select a chat", session_options)

if selected == "➕ New Chat":
    cur.execute("INSERT INTO chat_sessions (user_id, title) VALUES (%s, %s) RETURNING id", (user_id, "New Chat"))
    session_id = cur.fetchone()[0]
    conn.commit()
else:
    session_id = int(selected.split("ID")[1].strip().replace(")", ""))

# ---------- Load Messages ----------
cur.execute("SELECT role, content FROM chat_messages WHERE session_id=%s ORDER BY created_at ASC", (session_id,))
messages = cur.fetchall()

if "message" not in st.session_state:
    st.session_state.message = []

if not st.session_state.message:
    for role, content in messages:
        st.session_state.message.append({"role": role, "content": content})

# Display messages
for message in st.session_state.message:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ---------- Embeddings ----------
with open("json_file/scraping_embeddings.json", "r") as f:
    data = json.load(f)

texts = [item["text"] for item in data]
embeddings = np.array([item["embedding"] for item in data])
model = SentenceTransformer("all-mpnet-base-v2")

def fetchh(question):
    embedding = model.encode([question])[0]
    cur.execute("""
        SELECT content FROM embedding
        ORDER BY embedding <-> %s::vector
        LIMIT 1
    """, (embedding.tolist(),))
    result = cur.fetchone()
    return result[0] if result else None

def generate_answer_with_ollama(query, context):
    prompt = f"""
You are a helpful assistant. Use ONLY the context below to answer the question. 
If you don't know the answer from the context, say "I don't know based on the document."

Context:
{context}

Question:
{query}

Answer:
"""
    response = ollama.chat(
        model="mistral",  
        messages=[{"role": "user", "content": prompt}]
    )
    return response['message']['content'].strip()

# ---------- Chat Input ----------
st.title("Welcome to Chatbot")

query = st.chat_input("Ask something about your data:")

if query:
    # Save user msg
    cur.execute("INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
                (session_id, "user", query))
    conn.commit()
    st.session_state.message.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Fetch context
    context = fetchh(query)
    if not context:
        context = "I don't know based on the document."
    
    # AI response
    answer = generate_answer_with_ollama(query, context)
    cur.execute("INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
                (session_id, "assistant", answer))
    conn.commit()
    st.session_state.message.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
