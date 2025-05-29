import streamlit as st
from summarizer import summarize_url, build_conversational_chain, translate_text

st.set_page_config(page_title="AI News Summarizer", layout="centered")
st.title("📰 AI News Summarizer")

# Model selection dropdown
model_options = ["gpt-4.1-nano", "gpt-4.1-mini"]
selected_model = st.selectbox("Select AI model:", model_options, index=0)

st.markdown(f"Paste any news homepage URL or click one of the sources below to get a summary powered by {selected_model}.")
st.markdown("<div style='color: gray; font-size: 0.9em;'>💬 <b>New(29 May 2025):</b> You can now translate summaries between English and Chinese with a single click and choose between gpt-4.1-nano or gpt-4.1-mini models!</div>", unsafe_allow_html=True)

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
            summary_dict = summarize_url(url, model=selected_model)
            st.session_state["summary_dict"] = summary_dict
            st.session_state["original_language"] = summary_dict["language"]
            st.session_state["current_language"] = summary_dict["language"]
            st.session_state["chat_chain"] = build_conversational_chain(summary_dict, model=selected_model)
            st.session_state["chat_history"] = [] 


# === Chat about the summary ===
if "summary_dict" in st.session_state:
    st.markdown("### ✅ Summary")
    
    # Add translation button
    col1, col2 = st.columns([5, 1])
    with col2:
        original_lang = st.session_state["original_language"]
        current_lang = st.session_state["current_language"]
        target_lang = "en" if current_lang == "zh" else "zh"
        button_text = "Translate to English" if target_lang == "en" else "Translate to Chinese"
        
        if st.button("🔄 Translate", key="translate_button"):
            with st.spinner("Translating..."):
                # Determine which language to translate to
                new_target_lang = "en" if current_lang == "zh" else "zh"
                
                # Check if we already have this translation
                translation_key = f"{new_target_lang}_content"
                if translation_key in st.session_state["summary_dict"]:
                    # Use cached translation
                    st.session_state["current_language"] = new_target_lang
                else:
                    # Generate new translation
                    translated_content = translate_text(
                        st.session_state["summary_dict"]["content"],
                        new_target_lang,
                        model=selected_model
                    )
                    # Store translation
                    st.session_state["summary_dict"][translation_key] = translated_content
                    st.session_state["current_language"] = new_target_lang
                
                # Force rerun to update UI
                st.rerun()
    
    # Display summary in current language
    current_lang = st.session_state["current_language"]
    original_lang = st.session_state["original_language"]
    
    if current_lang == original_lang:
        summary_content = st.session_state["summary_dict"]["content"]
    elif current_lang == "en" and "en_content" in st.session_state["summary_dict"]:
        summary_content = st.session_state["summary_dict"]["en_content"]
    elif current_lang == "zh" and "zh_content" in st.session_state["summary_dict"]:
        summary_content = st.session_state["summary_dict"]["zh_content"]
    else:
        summary_content = st.session_state["summary_dict"]["content"]
    
    st.markdown(summary_content)

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
