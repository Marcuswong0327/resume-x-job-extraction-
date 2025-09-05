import streamlit as st

# Import the pages
from pages import resume_parser, job_extractor

def main():
    st.set_page_config(
        page_title="Resume Parser & Job Extractor",
        page_icon="📄",
        layout="wide"
    )
    
    # Sidebar for navigation
    with st.sidebar:
        # Page selection with square icons
        page = st.radio(
            "",
            ["📄 Resume Parser", "💼 Job Extractor"],
            index=0
        )
    
    # Route to appropriate page
    if page == "📄 Resume Parser":
        resume_parser.show_page()
    elif page == "💼 Job Extractor":
        job_extractor.show_page()

if __name__ == "__main__":
    main()
