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
import re
from urllib.parse import urljoin
import json

load_dotenv()
client = OpenAI()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

SYSTEM_PROMPT = "You are a helpful assistant that summarizes homepage content from news websites. For each news item, include a clickable link icon or embed the URL in the text without displaying the full URL."

def translate_text(text: str, target_language: str, model: str = "gpt-4.1-nano") -> str:
    """Translate text between English and Chinese"""
    if not text or text.startswith("❌"):
        return text
        
    source_language = "Chinese" if any('\u4e00' <= char <= '\u9fff' for char in text) else "English"
    target_language_name = "Chinese" if target_language == "zh" else "English"
    
    if source_language == target_language_name:
        return text
        
    try:
        prompt = f"""Translate the following text from {source_language} to {target_language_name}. 
        Maintain the same markdown formatting, links, and structure in the translation.
        
        Text to translate:
        {text}
        """
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional translator between English and Chinese."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Translation Error: {e}"

def summarize_url(url: str, model: str = "gpt-4.1-nano") -> dict:
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {
            "content": f"❌ Failed to fetch the page: {e}",
            "language": "en"
        }

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract headlines and their URLs before removing tags
        news_links = []
        for a_tag in soup.find_all('a'):
            # Skip empty links or those without text
            if not a_tag.get_text(strip=True) or not a_tag.get('href'):
                continue
                
            # Get the text and href
            text = a_tag.get_text(strip=True)
            href = a_tag.get('href')
            
            # Skip very short text or navigation links
            if len(text) < 20 or re.search(r'(login|sign in|subscribe|contact|about|menu)', text.lower()):
                continue
                
            # Convert relative URLs to absolute
            if not href.startswith(('http://', 'https://')):
                href = urljoin(url, href)
                
            # Add to our collection
            news_links.append({'text': text, 'url': href})
        
        # Limit to top 30 links to avoid overwhelming
        news_links = news_links[:30]
        
        # Now proceed with the regular text extraction
        for tag in soup(["script", "style", "nav", "footer", "noscript", "form", "img"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = list(set(line.strip() for line in text.splitlines() if len(line.strip()) > 30))
        limited_text = "\n".join(lines[:80])
    except Exception as e:
        return {
            "content": f"❌ Failed to extract text: {e}",
            "language": "en"
        }

    # Prepare the news links data
    news_links_text = ""
    if news_links:
        news_links_text = "\n\nHere are some of the headlines with their URLs:\n"
        for i, item in enumerate(news_links):
            news_links_text += f"\n{i+1}. {item['text']} - {item['url']}"
    
    prompt = f"""
You are reading the homepage of a news website. The content below contains headlines, subheadings, and key blurbs from that homepage.

Please summarize the **key stories, themes, and highlights** as a list in Markdown format and in source language(if the most of content is in English then summarize in English. If in Chinese, summarize in Chinese. There will not be any other languages. It should either Chinese or English). Group related items if possible.

IMPORTANT: For each news item, include a clickable link to the article where available. You can either:
1. Add a link icon like [🔗](URL) after the news item
2. Or embed the URL in part of the text like [read more](URL)
3. DO NOT display the full URL in the text

If you cannot find a matching URL for a news item, it's okay to leave it without a link.

---
{limited_text}
{news_links_text}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        summary_content = response.choices[0].message.content
        # Detect language - simple check for Chinese characters
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in summary_content)
        language = 'zh' if is_chinese else 'en'
        return {
            "content": summary_content,
            "language": language
        }
    except Exception as e:
        return {
            "content": f"❌ GPT Error: {e}",
            "language": "en"
        }

def build_conversational_chain(summary_dict: dict, model: str = "gpt-4.1-nano"):
    summary_text = summary_dict["content"]
    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    doc = Document(page_content=summary_text)
    chunks = text_splitter.split_documents([doc])

    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(chunks, embedding=embeddings)
    retriever = vectorstore.as_retriever()
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    llm = ChatOpenAI(model_name=model, temperature=0.5)
    chain = ConversationalRetrievalChain.from_llm(llm, retriever=retriever, memory=memory)
    return chain