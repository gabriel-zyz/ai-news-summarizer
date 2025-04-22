import streamlit as st
from summarizer import summarize_url

st.set_page_config(page_title="AI News Summarizer", layout="centered")

st.title("📰 AI News Summarizer")
st.markdown("Paste any news homepage URL, or click one of the quick sources below to get a summary powered by GPT-4o or GPT-3.5-turbo.")

# --- Quick Sources ---
default_sources = {
    "US": {
        "CNN": "https://www.cnn.com",
        "NYTimes": "https://www.nytimes.com",
        "NPR": "https://www.npr.org",
        "The Washington Post": "https://www.washingtonpost.com",
        "ABC News": "https://abcnews.go.com",
        "NBC News": "https://www.nbcnews.com",
        "CBS News": "https://www.cbsnews.com",
        "Fox News": "https://www.foxnews.com",
        "NBA News": "https://www.nba.com/news",
        "Bloomberg": "https://www.bloomberg.com"
    },
    "Australia": {
        "ABC News AU": "https://www.abc.net.au/news",
        "SMH": "https://www.smh.com.au",
        "The Guardian AU": "https://www.theguardian.com/au",
        "The Age": "https://www.theage.com.au",
        "The Conversation": "https://theconversation.com/au",
        "7News": "https://7news.com.au",
        "SBS News": "https://www.sbs.com.au/news",
        "Sky News Australia": "https://www.skynews.com.au/",
        "9News": "https://www.9news.com.au/melbourne",
        "Crikey": "https://www.crikey.com.au"
    },
    "Taiwan": {
        "UDN 聯合報": "https://udn.com/news/breaknews/1",
        "CNA 中央社": "https://www.cna.com.tw",
        "Liberty Times 自由時報": "https://news.ltn.com.tw",
        "Apple News 蘋果新聞網": "https://tw.nextapple.com",
        "TVBS": "https://news.tvbs.com.tw",
        "SETN 三立新聞網": "https://www.setn.com",
        "ETtoday": "https://www.ettoday.net",
        "NOWnews 今日新聞": "https://www.nownews.com",
        "Initium Media 端傳媒": "https://theinitium.com/zh-hans/latest",
        "Storm Media 風傳媒": "https://www.storm.mg"
    },
    "China": {
        "Xinhua 新華網": "https://www.news.cn",
        "People's Daily 人民網": "http://www.people.com.cn",
        "Huanqiu 環球網": "https://www.huanqiu.com/",
        "The Paper 澎湃新聞": "https://m.thepaper.cn/",
        "CCTV News 央視新聞": "https://news.cctv.com",
        "China Daily": "https://www.chinadaily.com.cn",
        "Sina News": "https://news.sina.com.cn",
        "Tencent News": "https://www.qq.com/",
        "Phoenix News": "https://news.ifeng.com",
        "Netease News": "https://news.163.com"
    }
}

# --- Quick Buttons ---
st.markdown("### 🔗 Quick Sources by Region")

for region, sources in default_sources.items():
    with st.expander(region):
        cols = st.columns(2)
        buttons = list(sources.items())
        half = len(buttons) // 2 + len(buttons) % 2
        for i, (label, url) in enumerate(buttons):
            col = cols[0] if i < half else cols[1]
            if col.button(label, key=url):
                st.session_state.url = url

# --- URL Input ---
st.markdown("### 🔍 Or enter a custom homepage URL")
url = st.text_input("News homepage URL", value=st.session_state.get("url", ""), key="url_input")

# --- Summarize ---
st.markdown("### ⚙️ Model Selection")
model_choice = st.selectbox(
    "Choose the model for summarization:",
    options=["gpt-3.5-turbo", "gpt-4.1-nano"],
    index=1
)

if st.button("Summarize This Page"):
    if not url:
        st.warning("Please enter or select a URL first.")
    else:
        with st.spinner("Fetching and summarizing homepage..."):
            summary = summarize_url(url, model=model_choice)
        st.markdown("### ✅ Summary")
        st.markdown(summary)