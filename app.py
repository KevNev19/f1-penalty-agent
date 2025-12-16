"""Streamlit Chat Interface for F1 Penalty Agent."""

import os
import streamlit as st

# Set page config first (must be first Streamlit command)
st.set_page_config(
    page_title="F1 Penalty Agent",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Simple, clean styling
st.markdown("""
<style>
    /* Clean header */
    .header-container {
        background: linear-gradient(90deg, #e10600 0%, #ff1801 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
        color: white;
    }
    
    /* Source box styling */
    .source-box {
        background-color: #f0f2f6;
        border-left: 4px solid #e10600;
        padding: 0.75rem 1rem;
        margin-top: 1rem;
        border-radius: 0 5px 5px 0;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-container">
    <h1 style="margin:0; font-size: 2rem;">🏎️ F1 Penalty Agent</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Ask me anything about Formula 1 penalties, regulations, and stewards decisions</p>
</div>
""", unsafe_allow_html=True)


def init_agent():
    """Initialize the F1 Agent (cached)."""
    from src.config import settings
    from src.rag.vectorstore import VectorStore
    from src.rag.retriever import F1Retriever
    from src.llm.gemini_client import GeminiClient
    from src.agent.f1_agent import F1Agent
    
    chroma_host = os.environ.get("CHROMA_HOST", settings.chroma_host)
    
    vector_store = VectorStore(
        settings.chroma_persist_dir,
        settings.google_api_key,
        chroma_host=chroma_host,
        chroma_port=settings.chroma_port,
    )
    
    retriever = F1Retriever(vector_store)
    llm_client = GeminiClient(settings.google_api_key)
    agent = F1Agent(llm_client, retriever)
    
    return agent, vector_store


@st.cache_resource
def get_agent():
    """Get cached agent instance."""
    return init_agent()


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    try:
        with st.spinner("Connecting to F1 knowledge base..."):
            agent, vector_store = get_agent()
            st.session_state.agent = agent
            st.session_state.vector_store = vector_store
            st.session_state.connected = True
    except Exception as e:
        st.session_state.connected = False
        st.session_state.error = str(e)

# Sidebar
with st.sidebar:
    st.markdown("### 📊 Status")
    
    if st.session_state.get("connected", False):
        st.success("Connected to ChromaDB")
        
        try:
            vs = st.session_state.vector_store
            st.markdown("**Knowledge Base:**")
            for collection in ["f1_regulations", "stewards_decisions", "race_data"]:
                s = vs.get_collection_stats(collection)
                st.markdown(f"• {collection}: **{s['count']}** docs")
        except Exception:
            pass
    else:
        st.error("Not Connected")
        if "error" in st.session_state:
            st.code(st.session_state.error)
    
    st.markdown("---")
    st.markdown("### 💡 Try These Questions")
    
    examples = [
        "What is a 5 second penalty?",
        "Explain track limits",
        "Reprimand vs penalty?",
        "How does safety car work?",
    ]
    
    for q in examples:
        if st.button(q, key=f"ex_{q}", use_container_width=True):
            st.session_state.pending_question = q
            st.rerun()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("sources"):
            with st.expander("📚 View Sources"):
                for src in message["sources"][:3]:
                    st.caption(src)

# Handle pending question from sidebar
if "pending_question" in st.session_state:
    prompt = st.session_state.pending_question
    del st.session_state.pending_question
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    if st.session_state.get("connected", False):
        with st.chat_message("assistant"):
            with st.spinner("Searching regulations & stewards decisions..."):
                try:
                    response = st.session_state.agent.ask(prompt)
                    st.write(response.answer)
                    
                    if response.sources_used:
                        with st.expander("📚 View Sources"):
                            for src in response.sources_used[:3]:
                                st.caption(src)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.answer,
                        "sources": response.sources_used,
                    })
                except Exception as e:
                    st.error(f"Error: {e}")
    st.rerun()

# Chat input
if prompt := st.chat_input("Ask about F1 penalties and regulations..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)
    
    if st.session_state.get("connected", False):
        with st.chat_message("assistant"):
            with st.spinner("Searching regulations & stewards decisions..."):
                try:
                    response = st.session_state.agent.ask(prompt)
                    st.write(response.answer)
                    
                    if response.sources_used:
                        with st.expander("📚 View Sources"):
                            for src in response.sources_used[:3]:
                                st.caption(src)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.answer,
                        "sources": response.sources_used,
                    })
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        with st.chat_message("assistant"):
            st.error("Not connected to knowledge base. Check configuration.")

# Footer
st.markdown("---")
st.caption("F1 Penalty Agent POC | Powered by Gemini AI & ChromaDB")
