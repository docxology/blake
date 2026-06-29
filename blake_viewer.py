#!/usr/bin/env python3
"""
Simple Blake text viewer - directly loads texts from texts_clean directory.
Uses Streamlit to display Blake's works without requiring database ingestion.
"""

import streamlit as st
from pathlib import Path
import re

# Page config
st.set_page_config(
    page_title="Blake Works Explorer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Data directory
TEXTS_DIR = Path(__file__).parent / "data" / "blake" / "texts_clean"

def extract_title(content: str) -> str:
    """Extract title from Gutenberg text."""
    match = re.search(r"Title:\s*(.+)", content)
    if match:
        return match.group(1).strip()
    return "Unknown Title"

def extract_author(content: str) -> str:
    """Extract author from Gutenberg text."""
    match = re.search(r"Author:\s*(.+)", content)
    if match:
        return match.group(1).strip()
    return "William Blake"

def get_text_content(content: str) -> str:
    """Extract main text content (between START and END markers)."""
    start_match = re.search(r"\*\*\* START OF.*?\*\*\*", content)
    end_match = re.search(r"\*\*\* END OF.*?\*\*\*", content)
    
    if start_match and end_match:
        return content[start_match.end():end_match.start()].strip()
    return content

def load_all_texts():
    """Load all text files from texts_clean directory."""
    texts = []
    if TEXTS_DIR.exists():
        for file in sorted(TEXTS_DIR.glob("*.txt")):
            try:
                content = file.read_text(encoding='utf-8-sig')
                title = extract_title(content)
                author = extract_author(content)
                main_text = get_text_content(content)
                texts.append({
                    'filename': file.name,
                    'title': title,
                    'author': author,
                    'content': main_text,
                    'full_content': content,
                    'size': len(content)
                })
            except Exception as e:
                st.error(f"Error loading {file.name}: {e}")
    return texts

# Main app
st.title("📚 Blake Works Explorer")
st.markdown("Explore locally available Blake texts with interactive search and analysis.")

# Load texts
texts = load_all_texts()

# Sidebar
with st.sidebar:
    st.header("Navigation")
    st.metric("Total Works", len(texts))
    st.metric("Total Characters", sum(t['size'] for t in texts))
    
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Main content tabs
tab1, tab2, tab3 = st.tabs(["📖 Browse Works", "🔍 Search", "📊 Analysis"])

with tab1:
    st.header("Browse Blake's Works")
    
    if not texts:
        st.warning(f"No texts found in {TEXTS_DIR}")
        st.info("Please run the download script to populate texts.")
    else:
        for text in texts:
            with st.expander(f"📜 {text['title']} ({text['author']})"):
                st.write(f"**File:** {text['filename']}")
                st.write(f"**Size:** {text['size']:,} characters")
                st.divider()
                st.text_area(
                    "Content",
                    text['content'][:5000] + ("..." if len(text['content']) > 5000 else ""),
                    height=400,
                    disabled=True
                )
                if len(text['content']) > 5000:
                    st.info(f"Showing first 5000 of {len(text['content']):,} characters")

with tab2:
    st.header("Search Blake's Works")
    
    search_query = st.text_input("Search Query", placeholder="Enter keywords (e.g., Tyger, Lamb, Heaven)")
    
    if search_query and texts:
        results = []
        for text in texts:
            matches = list(re.finditer(re.escape(search_query), text['content'], re.IGNORECASE))
            if matches:
                results.append({
                    'text': text,
                    'matches': matches,
                    'count': len(matches)
                })
        
        st.subheader(f"Search Results ({sum(r['count'] for r in results)} matches in {len(results)} works)")
        
        for result in sorted(results, key=lambda x: x['count'], reverse=True):
            with st.expander(f"📜 {result['text']['title']} ({result['count']} matches)"):
                for i, match in enumerate(result['matches'][:10]):
                    start = max(0, match.start() - 100)
                    end = min(len(result['text']['content']), match.end() + 100)
                    context = result['text']['content'][start:end]
                    highlighted = context.replace(
                        search_query, 
                        f"**{search_query}**"
                    )
                    st.markdown(f"...{highlighted}...")
                    st.divider()
                if result['count'] > 10:
                    st.info(f"Showing 10 of {result['count']} matches")

with tab3:
    st.header("Text Analysis")
    
    if texts:
        st.subheader("Works Overview")
        
        # Basic stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Works", len(texts))
        with col2:
            total_words = sum(len(t['content'].split()) for t in texts)
            st.metric("Total Words", f"{total_words:,}")
        with col3:
            st.metric("Total Characters", f"{sum(t['size'] for t in texts):,}")
        
        # Works table
        st.subheader("Works by Size")
        for text in sorted(texts, key=lambda x: x['size'], reverse=True):
            word_count = len(text['content'].split())
            st.write(f"- **{text['title']}**: {word_count:,} words ({text['size']:,} chars)")
