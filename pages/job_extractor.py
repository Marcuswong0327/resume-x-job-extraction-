import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import io
from datetime import datetime

def show_page():
    """Job Extractor page"""
    st.title("💼 Job Data Extractor")
    st.markdown("Extract job listings from Seek and Jobstreet websites")
    
    # Initialize session state
    if 'extracted_jobs' not in st.session_state:
        st.session_state.extracted_jobs = []
    if 'extraction_in_progress' not in st.session_state:
        st.session_state.extraction_in_progress = False
    if 'extraction_complete' not in st.session_state:
        st.session_state.extraction_complete = False
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Job Search URL")
        job_url = st.text_input(
            "Enter Seek or Jobstreet job search URL:",
            placeholder="https://www.seek.com.au/Quantity-Surveyor-OR-estimator-jobs-in-construction/in-Queensland-QLD?pos=3",
            help="Paste the full URL from your job search results page"
        )
        
        # Validate URL
        url_valid = False
        if job_url:
            if 'seek.com' in job_url.lower() or 'jobstreet.com' in job_url.lower():
                url_valid = True
                st.success("✅ Valid job search URL detected")
            else:
                st.error("❌ Please enter a valid Seek or Jobstreet URL")
        
        # Extract button
        extract_disabled = not url_valid or st.session_state.extraction_in_progress
        
        if st.button("Extract Jobs", type="primary", use_container_width=True, disabled=extract_disabled):
            if url_valid:
                extract_jobs(job_url)
    
    with col2:
        st.subheader("Extraction Status")
        
        if st.session_state.extraction_in_progress:
            st.info("🔄 Extracting job data...")
        elif st.session_state.extracted_jobs:
            st.metric("Jobs Found", len(st.session_state.extracted_jobs))
            
            if st.session_state.extraction_complete:
                st.success("✅ Extraction complete!")
                
                if st.button("Download CSV", type="secondary", use_container_width=True):
                    download_csv()
        else:
            st.info("Enter a job search URL to begin extraction")
    
    # Display extracted jobs
    if st.session_state.extracted_jobs:
        st.subheader("Extracted Jobs")
        
        # Create DataFrame for display (without job URL column)
        display_data = []
        for job in st.session_state.extracted_jobs:
            display_data.append({
                'Job Title': job.get('job_title', ''),
                'Company': job.get('company', ''),
                'Location': job.get('location', '')
            })
        
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True)
        
        # Show extraction summary
        st.info(f"📊 Total jobs extracted: {len(st.session_state.extracted_jobs)}")

def extract_jobs(url):
    """Extract jobs from the given URL"""
    st.session_state.extraction_in_progress = True
    st.session_state.extraction_complete = False
    st.session_state.extracted_jobs = []
    
    try:
        # Determine website type
        website_type = 'seek' if 'seek.com' in url.lower() else 'jobstreet'
        
        # Progress tracking
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        page_count = 1
        max_pages = 50  # Safety limit
        all_jobs = []
        
        current_url = url
        
        while page_count <= max_pages:
            try:
                status_text.text(f"Extracting page {page_count}... ({len(all_jobs)} jobs found)")
                progress_bar.progress(min((page_count / 10) * 100, 90) / 100)
                
                # Make request with comprehensive headers to avoid blocking
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                }
                
                # Create a session to maintain cookies
                session = requests.Session()
                session.headers.update(headers)
                
                try:
                    response = session.get(current_url, timeout=30)
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 403:
                        st.warning(f"⚠️ Access denied (403) for page {page_count}. This website may be blocking automated requests. Try using a different search URL or check if the website has anti-bot protection.")
                        break
                    else:
                        raise e
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract jobs based on website type
                if website_type == 'seek':
                    page_jobs = extract_seek_jobs(soup)
                else:
                    page_jobs = extract_jobstreet_jobs(soup)
                
                if not page_jobs and page_count > 1:
                    break  # No more jobs found
                
                all_jobs.extend(page_jobs)
                
                # Look for next page
                next_url = find_next_page_url(soup, website_type, current_url)
                if not next_url:
                    break  # No more pages
                
                current_url = next_url
                page_count += 1
                
                # No delay - direct extraction like the Chrome extension
                
            except Exception as e:
                st.warning(f"Error extracting page {page_count}: {str(e)}")
                break
        
        # Final progress update
        progress_bar.progress(1.0)
        status_text.text(f"Extraction complete! Found {len(all_jobs)} jobs across {page_count-1} pages")
        
        st.session_state.extracted_jobs = all_jobs
        st.session_state.extraction_complete = True
        
        if all_jobs:
            st.success(f"Successfully extracted {len(all_jobs)} jobs from {page_count-1} pages")
        else:
            st.warning("No jobs were found. The website structure may have changed.")
            
    except Exception as e:
        st.error(f"An error occurred during extraction: {str(e)}")
        
    finally:
        st.session_state.extraction_in_progress = False

def extract_seek_jobs(soup):
    """Extract job data from Seek page - using Chrome extension logic"""
    jobs = []
    
    # Use exact selectors from Chrome extension
    job_cards = soup.select('[data-automation="normalJob"], [data-testid="job-card"], article[data-automation], .job-card, [data-cy="job-item"]')
    
    for card in job_cards:
        try:
            # Extract job title - multiple selectors like the extension
            title_elem = card.select_one('[data-automation="jobTitle"] a, [data-automation="job-title"] a, h3 a, h2 a, .job-title a, [data-testid="job-title"] a')
            job_title = title_elem.get_text(strip=True) if title_elem else 'N/A'
            
            # Extract company name
            company_elem = card.select_one('[data-automation="jobCompany"] a, [data-automation="jobCompany"], [data-automation="job-company"], .company-name, [data-testid="job-company"]')
            company = company_elem.get_text(strip=True) if company_elem else 'N/A'
            
            # Extract location
            location_elem = card.select_one('[data-automation="jobLocation"] a, [data-automation="jobLocation"], [data-automation="job-location"], .job-location, [data-testid="job-location"]')
            location = location_elem.get_text(strip=True) if location_elem else 'N/A'
            
            if job_title != 'N/A' or company != 'N/A':
                jobs.append({
                    'job_title': job_title,
                    'company': company,
                    'location': location
                })
                
        except Exception as e:
            continue
    
    return jobs

def extract_jobstreet_jobs(soup):
    """Extract job data from Jobstreet page - using Chrome extension logic"""
    jobs = []
    
    # Use exact selectors from Chrome extension
    job_cards = soup.select('[data-automation="job-list-item"], .job-item, .job-card, [data-testid="job-card"], .job, article[data-cy]')
    
    for card in job_cards:
        try:
            # Extract job title - multiple selectors like the extension
            title_elem = card.select_one('h2 a, h3 a, .job-title a, [data-automation="job-title"] a, [data-testid="job-title"] a, a[data-automation="jobTitle"]')
            job_title = title_elem.get_text(strip=True) if title_elem else 'N/A'
            
            # Extract company name
            company_elem = card.select_one('[data-automation="job-company"], .company-name, .job-company, [data-testid="job-company"], .company')
            company = company_elem.get_text(strip=True) if company_elem else 'N/A'
            
            # Extract location
            location_elem = card.select_one('[data-automation="job-location"], .location, .job-location, [data-testid="job-location"], .job-location-text')
            location = location_elem.get_text(strip=True) if location_elem else 'N/A'
            
            if job_title != 'N/A' or company != 'N/A':
                jobs.append({
                    'job_title': job_title,
                    'company': company,
                    'location': location
                })
                
        except Exception as e:
            continue
    
    return jobs

def find_next_page_url(soup, website_type, current_url):
    """Find the next page URL"""
    try:
        if website_type == 'seek':
            # Look for next page button
            next_link = soup.find('a', attrs={'data-automation': lambda x: x and 'page-next' in x}) or \
                       soup.find('a', class_=lambda x: x and 'next' in x.lower())
            
            if next_link and next_link.get('href'):
                href = next_link.get('href')
                if href.startswith('http'):
                    return href
                else:
                    return f"https://www.seek.com.au{href}"
        
        else:  # jobstreet
            next_link = soup.find('a', class_=lambda x: x and 'next' in x.lower()) or \
                       soup.find('a', attrs={'data-automation': lambda x: x and 'next' in x})
            
            if next_link and next_link.get('href'):
                href = next_link.get('href')
                if href.startswith('http'):
                    return href
                else:
                    return f"https://www.jobstreet.com{href}"
    
    except Exception:
        pass
    
    return None

def download_csv():
    """Generate and download CSV file"""
    try:
        if not st.session_state.extracted_jobs:
            st.warning("No job data to export.")
            return
        
        # Create DataFrame (without job URL column)
        df_data = []
        for job in st.session_state.extracted_jobs:
            df_data.append({
                'Job Title': job.get('job_title', ''),
                'Company': job.get('company', ''),
                'Location': job.get('location', '')
            })
        
        df = pd.DataFrame(df_data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"job_data_{timestamp}.csv"
        
        # Provide download
        st.download_button(
            label="📥 Download CSV File",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            use_container_width=True
        )
        
        st.success(f"CSV file ready for download: {filename}")
        
    except Exception as e:
        st.error(f"Error generating CSV: {str(e)}")
