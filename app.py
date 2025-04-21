import streamlit as st
from summarizer import summarize_url

st.set_page_config(page_title="AI News Summarizer", layout="centered")

st.title("📰 AI News Summarizer")
st.markdown("Paste any news homepage URL, or click one of the quick sources below to get a summary powered by GPT-4o.")

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
        "Reuters": "https://www.reuters.com",
        "Bloomberg": "https://www.bloomberg.com"
    },
    "Australia": {
        "ABC News AU": "https://www.abc.net.au/news",
        "SMH": "https://www.smh.com.au",
        "The Guardian AU": "https://www.theguardian.com/au",
        "The Age": "https://www.theage.com.au",
        "News.com.au": "https://www.news.com.au",
        "7News": "https://7news.com.au",
        "SBS News": "https://www.sbs.com.au/news",
        "The Australian": "https://www.theaustralian.com.au",
        "The West Australian": "https://thewest.com.au",
        "Crikey": "https://www.crikey.com.au"
    },
    "Taiwan": {
        "UDN 聯合報": "https://udn.com",
        "CNA 中央社": "https://www.cna.com.tw",
        "Liberty Times 自由時報": "https://news.ltn.com.tw",
        "Apple News 蘋果新聞網": "https://tw.nextapple.com",
        "TVBS": "https://news.tvbs.com.tw",
        "SETN 三立新聞網": "https://www.setn.com",
        "ETtoday": "https://www.ettoday.net",
        "NOWnews 今日新聞": "https://www.nownews.com",
        "China Times 中時": "https://www.chinatimes.com",
        "Storm Media 風傳媒": "https://www.storm.mg"
    },
    "China": {
        "Xinhua 新華網": "https://www.news.cn",
        "People's Daily 人民網": "http://www.people.com.cn",
        "Global Times 環球時報": "https://www.globaltimes.cn",
        "The Paper 澎湃新聞": "https://www.thepaper.cn",
        "CCTV News": "https://news.cctv.com",
        "China Daily": "https://www.chinadaily.com.cn",
        "Sina News": "https://news.sina.com.cn",
        "Tencent News": "https://xw.qq.com",
        "Phoenix News": "https://news.ifeng.com",
        "Netease News": "https://news.163.com"
    }
}

# --- Quick Buttons ---
st.markdown("### 🔗 Quick Sources by Region")

for region, sources in default_sources.items():
    with st.expander(region, expanded=(region == "US")):
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
if st.button("Summarize This Page"):
    if not url:
        st.warning("Please enter or select a URL first.")
    else:
        with st.spinner("Fetching and summarizing homepage..."):
            summary = summarize_url(url)
        st.markdown("### ✅ Summary")
        st.markdown(summary)