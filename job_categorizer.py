import streamlit as st
import pandas as pd
import base64
import traceback
from company_categorizer import CompanyCategorizer
from excel_exporter import ExcelExporter

def job_categorizer_page():
    """Job Categorizer page for categorizing companies in Excel job data"""
    
    st.title("🏢 Job Categorizer")
    st.write("Upload an Excel file with job data to categorize companies by business nature")
    
    # Initialize session state for job categorizer
    if 'job_data' not in st.session_state:
        st.session_state.job_data = []
    if 'categorization_complete' not in st.session_state:
        st.session_state.categorization_complete = False
    if 'categorization_in_progress' not in st.session_state:
        st.session_state.categorization_in_progress = False
    
    # Check API key availability
    api_key_available = check_api_key()
    
    # File upload section
    st.header("📁 Upload Excel File")
    uploaded_file = st.file_uploader(
        "Choose an Excel file with job data",
        type=['xlsx', 'xls'],
        help="Excel file should contain columns: Job Title, Company, Location, Salary, Job URL"
    )
    
    if uploaded_file:
        try:
            # Read the Excel file
            df = pd.read_excel(uploaded_file)
            
            # Validate required columns
            required_columns = ['Job Title', 'Company', 'Location', 'Salary', 'Job URL']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")
                st.write("Required columns: Job Title, Company, Location, Salary, Job URL")
                return
            
            # Display file info
            st.success(f"✅ File uploaded successfully: {len(df)} jobs found")
            
            # Show preview of data
            with st.expander("📋 Data Preview", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
            
            # Convert DataFrame to list of dictionaries
            jobs_data = df.to_dict('records')
            
            # Categorization section
            st.header("🔍 Company Categorization")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if api_key_available:
                    st.info("✅ AI categorization available (regex + AI fallback)")
                else:
                    st.warning("⚠️ Only regex categorization available (no API key)")
                
                process_disabled = st.session_state.categorization_in_progress
                
                if st.button("Categorize Companies", type="primary", use_container_width=True, disabled=process_disabled):
                    categorize_jobs(jobs_data)
            
            with col2:
                if st.session_state.categorization_in_progress:
                    st.info("Processing...")
                elif st.session_state.categorization_complete and st.session_state.job_data:
                    st.metric("Categorized Jobs", len(st.session_state.job_data))
                    
                    if st.button("Download Enhanced Excel", type="secondary", use_container_width=True):
                        download_categorized_excel()
            
            # Display categorized results
            if st.session_state.job_data and st.session_state.categorization_complete:
                st.header("📊 Categorized Results")
                
                # Create DataFrame for display
                results_df = pd.DataFrame(st.session_state.job_data)
                
                # Show statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    unique_categories = results_df['Business Nature'].nunique()
                    st.metric("Unique Categories", unique_categories)
                with col2:
                    unknown_count = len(results_df[results_df['Business Nature'] == 'Unknown'])
                    st.metric("Unknown Categories", unknown_count)
                with col3:
                    categorized_count = len(results_df[results_df['Business Nature'] != 'Unknown'])
                    st.metric("Successfully Categorized", categorized_count)
                
                # Show category distribution
                with st.expander("📈 Category Distribution", expanded=True):
                    category_counts = results_df['Business Nature'].value_counts()
                    st.bar_chart(category_counts)
                
                # Show full results
                st.subheader("Complete Results")
                st.dataframe(results_df, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error reading Excel file: {str(e)}")
            with st.expander("Error Details"):
                st.code(traceback.format_exc())

def check_api_key():
    """Check if OpenRouter API key is available"""
    try:
        if "DEEPSEEK_API_KEY" in st.secrets:
            return True
        return False
    except:
        return False

def categorize_jobs(jobs_data):
    """Process and categorize job data"""
    st.session_state.categorization_in_progress = True
    st.session_state.categorization_complete = False
    st.session_state.job_data = []
    
    try:
        # Initialize categorizer
        with st.spinner("Initializing categorizer..."):
            api_key = st.secrets.get("DEEPSEEK_API_KEY", "") if "DEEPSEEK_API_KEY" in st.secrets else ""
            categorizer = CompanyCategorizer(api_key)
        
        # Progress tracking
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # Categorize companies
        with st.spinner("Categorizing companies..."):
            status_text.text("Processing companies...")
            
            # Process in batches to show progress
            batch_size = 10
            total_jobs = len(jobs_data)
            categorized_jobs = []
            
            for i in range(0, total_jobs, batch_size):
                batch = jobs_data[i:i+batch_size]
                
                # Update progress
                progress = (i + len(batch)) / total_jobs
                progress_bar.progress(progress)
                status_text.text(f"Processing jobs {i+1}-{min(i+batch_size, total_jobs)} of {total_jobs}")
                
                # Categorize batch
                categorized_batch = categorizer.categorize_companies(batch)
                categorized_jobs.extend(categorized_batch)
        
        # Final progress update
        progress_bar.progress(1.0)
        status_text.text("Categorization complete!")
        
        # Store results
        st.session_state.job_data = categorized_jobs
        st.session_state.categorization_complete = True
        st.session_state.categorization_in_progress = False
        
        st.success(f"Successfully categorized {len(categorized_jobs)} jobs!")
        
    except Exception as e:
        st.error(f"Error during categorization: {str(e)}")
        st.session_state.categorization_in_progress = False
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def download_categorized_excel():
    """Generate and download Excel file with categorized data"""
    try:
        if not st.session_state.job_data:
            st.warning("No job data to export.")
            return

        with st.spinner("Generating Excel file..."):
            exporter = ExcelExporter()
            excel_data = exporter.export_jobs(st.session_state.job_data)

            # Encode to base64 for download
            b64 = base64.b64encode(excel_data).decode()
            filename = "categorized_jobs.xlsx"
            
            # Create download link
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Download Categorized Jobs Excel</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            st.success("Excel file ready for download!")

    except Exception as e:
        st.error(f"Error generating Excel file: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
