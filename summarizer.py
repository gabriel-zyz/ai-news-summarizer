import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"
}

SYSTEM_PROMPT = "You are a helpful assistant that summarizes homepage content from news websites. Your goal is to present the major headlines and themes in clear, bullet-pointed markdown."

def summarize_url(url: str, model: str = "gpt-4.1-nano") -> str:
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

    prompt = f"""You are reading the homepage of a news website. The content below contains headlines, subheadings, and key blurbs from that homepage.

Please summarize the **key stories, themes, and highlights** as a list in Markdown format and in source language. Group related items if possible.

---
{limited_text}
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
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ GPT Error: {e}"