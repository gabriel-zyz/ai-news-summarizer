import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

SYSTEM_PROMPT = "You are a helpful assistant that summarizes homepage content from news websites."

def summarize_url(url: str) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return f"❌ Failed to fetch the page: {e}"

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(["script", "style", "nav", "footer", "noscript", "form", "img"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = list(set(line.strip() for line in text.splitlines() if len(line.strip()) > 30))
        limited_text = "\n".join(lines[:80])
    except Exception as e:
        return f"❌ Failed to extract text: {e}"

    prompt = f"""
You are reading the homepage of a news website. The content below contains headlines, subheadings, and key blurbs from that homepage.

Please summarize the **key stories, themes, and highlights** as a list in Markdown format and in source language(if the most of content is in English then summarize in English. If in Chinese, summarize in Chinese. There will not be any other languages. It should either Chinese or English). Group related items if possible.

---
{limited_text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ GPT Error: {e}"

def build_conversational_chain(summary_text: str):
    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    doc = Document(page_content=summary_text)
    chunks = text_splitter.split_documents([doc])

    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(chunks, embedding=embeddings)
    retriever = vectorstore.as_retriever()
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    llm = ChatOpenAI(model_name="gpt-4.1-nano", temperature=0.5)
    chain = ConversationalRetrievalChain.from_llm(llm, retriever=retriever, memory=memory)
    return chain