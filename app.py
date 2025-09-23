import streamlit as st
from resume_parser_page import resume_parser_page
from job_categorizer import job_categorizer_page

def main():
    st.set_page_config(
        page_title="Resume Parser & Job Categorizer",
        page_icon="📄",
        layout="wide"
    )
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["Resume Parser", "Job Categorizer"]
    )
    
    # Route to appropriate page
    if page == "Resume Parser":
        resume_parser_page()
    elif page == "Job Categorizer":
        job_categorizer_page()

if __name__ == "__main__":
    main()
