import streamlit as st
from summarizer import summarize_url, build_conversational_chain

st.set_page_config(page_title="AI News Summarizer", layout="centered")
st.title("📰 AI News Summarizer")

st.markdown("Paste any news homepage URL or click one of the sources below to get a summary powered by GPT-4.1-nano.")
st.markdown("<div style='color: gray; font-size: 0.9em;'>💬 <b>New(11 May 2025):</b> You can now ask questions about the summary below using the built-in chatbot!</div>", unsafe_allow_html=True)

# Default sources
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
        "TechCrunch": "https://techcrunch.com"
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

st.markdown("### 🔗 Quick Sources by Region")
for region, sources in default_sources.items():
    with st.expander(region):
        cols = st.columns(3)
        for i, (label, url) in enumerate(sources.items()):
            if cols[i % 3].button(label, key=f"src-{label}"):
                st.session_state.url = url

url = st.text_input("Or enter a custom news homepage URL", value=st.session_state.get("url", ""), key="url_input")

if st.button("Summarize This Page"):
    if not url:
        st.warning("Please enter or select a URL first.")
    else:
        with st.spinner("Fetching and summarizing..."):
            summary = summarize_url(url)
            st.session_state["summary"] = summary
            st.session_state["chat_chain"] = build_conversational_chain(summary)
            st.session_state["chat_history"] = [] 


# === Chat about the summary ===
if "summary" in st.session_state:
    st.markdown("### ✅ Summary")
    st.markdown(st.session_state.summary)

    st.markdown("---")
    st.markdown("### 💬 Ask a question about this summary")

    # Initialize memory if not set
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Ask the question
    with st.form("chat_form"):
        user_query = st.text_input("Your question", key="chat_input")
        submitted = st.form_submit_button("Ask")

    # Run the LLM chain
    if submitted and user_query and st.session_state.get("chat_chain"):
        with st.spinner("Thinking..."):
            result = st.session_state.chat_chain.invoke({"question": user_query})
            st.session_state.chat_history.append(("You", user_query))
            st.session_state.chat_history.append(("AI", result["answer"]))

    # Display full conversation
    for role, msg in st.session_state.chat_history:
        st.markdown(f"**{role}:** {msg}")
