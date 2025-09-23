import re
import requests
import json
import streamlit as st
import time
import os
from typing import Optional

class CompanyCategorizer:
    """Handles company categorization using regex patterns and AI fallback"""
    
    def __init__(self, api_key=None):
        if not api_key:
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            
        self.api_key = api_key
        if self.api_key:
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
            self.headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Job Data Extractor - Company Categorization"
            }
    
    def categorize_with_regex(self, company_name: str) -> Optional[str]:
        """
        Categorize company using regex patterns
        
        Args:
            company_name: Name of the company
            
        Returns:
            Category name if pattern matches, None otherwise
        """
        if not company_name or company_name == 'N/A':
            return None

        name = company_name.lower()
        
        # Recruitment agency patterns
        recruitment_patterns = [
            r'recruit', r'people', r'talent', r'staffing', r'personnel', 
            r'executive', r'placement', r'workforce', r'consulting.*hr', 
            r'human.*resources', r'hr.*solutions', r'employment'
        ]
        
        if any(re.search(pattern, name, re.IGNORECASE) for pattern in recruitment_patterns):
            return 'Recruitment & Staffing'

        # Healthcare patterns
        health_patterns = [
            r'health', r'medical', r'hospital', r'clinic', r'pharma', 
            r'dental', r'care', r'wellness', r'therapy'
        ]
        
        if any(re.search(pattern, name, re.IGNORECASE) for pattern in health_patterns):
            return 'Healthcare Services'

        # Financial patterns
        finance_patterns = [
            r'bank', r'finance', r'insurance', r'investment', r'capital',
            r'credit', r'loan', r'wealth', r'fund', r'financial'
        ]
        
        if any(re.search(pattern, name, re.IGNORECASE) for pattern in finance_patterns):
            return 'Financial Services'

        # Education patterns
        education_patterns = [
            r'school', r'university', r'college', r'education', r'training',
            r'learning', r'academy', r'institute'
        ]
        
        if any(re.search(pattern, name, re.IGNORECASE) for pattern in education_patterns):
            return 'Education & Training'

        # Construction patterns
        construction_patterns = [
            r'construction', r'building', r'contractor', r'engineering', 
            r'architect', r'property', r'real.*estate', r'development'
        ]
        
        if any(re.search(pattern, name, re.IGNORECASE) for pattern in construction_patterns):
            return 'Construction & Engineering'

        # Retail patterns
        retail_patterns = [
            r'retail', r'shop', r'store', r'market', r'sales', r'commerce',
            r'fashion', r'clothing', r'goods'
        ]
        
        if any(re.search(pattern, name, re.IGNORECASE) for pattern in retail_patterns):
            return 'Retail & E-commerce'

        # Technology patterns
        tech_patterns = [
            r'tech', r'software', r'systems', r'digital', r'data', r'cyber',
            r'cloud', r'analytics', r'automation', r'ai', r'machine learning'
        ]
        
        if any(re.search(pattern, name, re.IGNORECASE) for pattern in tech_patterns):
            return 'Technology & Software'

        # Manufacturing patterns
        manufacturing_patterns = [
            r'manufacturing', r'factory', r'production', r'industrial', 
            r'automotive', r'steel', r'chemical', r'pharmaceutical'
        ]
        
        if any(re.search(pattern, name, re.IGNORECASE) for pattern in manufacturing_patterns):
            return 'Manufacturing'

        return None  # No pattern matched, will need AI categorization
    
    def categorize_company_with_ai(self, job_title: str, company_name: str) -> str:
        """
        Categorize company using AI when regex fails
        
        Args:
            job_title: Job title for context
            company_name: Name of the company
            
        Returns:
            Category name
        """
        if not self.api_key or not company_name or company_name == 'N/A':
            return 'Unknown'

        try:
            prompt = f"""Based on the company name "{company_name}" and Job Title "{job_title}", determine what this company does. 

If the company is well-known and you can confidently identify their main product(s) or service(s), respond with a short, specific phrase (2-5 words) describing it. 
Examples: "Wholesale Chicken Supply", "Construction Materials", "Retail Electronics & Furniture", "IT Cloud Services".

If the company is less known or there is limited information, classify it into a broad business category or industry sector only. 
Respond with a short, specific category name (2-4 words max). Dont give more than 6 words.
Examples: "Technology & Software", "Healthcare Services", "Financial Services", "Retail & E-commerce", "Manufacturing", "Consulting", "Education", "Construction", "Transportation", "Media & Entertainment", "Agriculture & Food".

If you are not sure, respond with "Unknown"."""

            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": "anthropic/claude-sonnet-4",
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "max_tokens": 50,
                    "temperature": 0.1
                },
                timeout=30
            )

            if response.status_code == 429:
                # Rate limited, wait and retry once
                time.sleep(2)
                return self.categorize_company_with_ai(job_title, company_name)
            
            if not response.ok:
                st.warning(f"API request failed for {company_name}: {response.status_code}")
                return 'Unknown'

            data = response.json()
            category = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            return category if category else 'Unknown'
            
        except Exception as e:
            st.warning(f"Error categorizing company {company_name} with AI: {str(e)}")
            return 'Unknown'
    
    def normalize_company_name(self, company_name: str) -> str:
        """
        Normalize company name for consistent processing
        
        Args:
            company_name: Raw company name
            
        Returns:
            Normalized company name
        """
        if not company_name or company_name == 'N/A':
            return company_name
        
        # Convert to lowercase and trim
        normalized = company_name.lower().strip()
        
        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove punctuation except & and -
        normalized = re.sub(r'[^\w\s&-]', '', normalized)
        
        # Remove common corporate suffixes
        suffixes_pattern = r'\b(pty\s+ltd|pte\s+ltd|sdn\s+bhd|ltd|limited|inc|incorporated|llc|plc|corp|corporation|company|co|gmbh|sa|srl|group|holdings|services|solutions|international|global|australia|aust)\b$'
        normalized = re.sub(suffixes_pattern, '', normalized, flags=re.IGNORECASE)
        
        # Remove "the" prefix
        normalized = re.sub(r'\b(the\s+)', '', normalized, flags=re.IGNORECASE)
        
        # Final cleanup of spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def categorize_companies(self, jobs_data: list) -> list:
        """
        Categorize all companies in the jobs data
        
        Args:
            jobs_data: List of job dictionaries
            
        Returns:
            Updated jobs data with Business Nature
        """
        if not jobs_data:
            return jobs_data
        
        # Track processing statistics
        total_companies = len(jobs_data)
        regex_matches = 0
        api_calls = 0
        processed = 0
        
        # Cache for normalized company names to avoid duplicate processing
        company_categories = {}
        
        for job in jobs_data:
            company = job.get('Company', '')
            job_title = job.get('Job Title', '')
            
            if company and company != 'N/A':
                processed += 1
                normalized_company = self.normalize_company_name(company)
                
                # Check if we've already categorized this normalized company
                if normalized_company in company_categories:
                    job['Business Nature'] = company_categories[normalized_company]
                    continue
                
                # Try regex pattern matching first
                regex_category = self.categorize_with_regex(company)
                if regex_category:
                    company_categories[normalized_company] = regex_category
                    job['Business Nature'] = regex_category
                    regex_matches += 1
                    continue
                
                # Fallback to AI categorization if API key is available
                if self.api_key:
                    ai_category = self.categorize_company_with_ai(job_title, company)
                    company_categories[normalized_company] = ai_category
                    job['Business Nature'] = ai_category
                    api_calls += 1
                    
                    # Add delay to avoid rate limiting
                    time.sleep(1.2)
                else:
                    # No API key available, mark as unknown
                    company_categories[normalized_company] = 'Unknown'
                    job['Business Nature'] = 'Unknown'
            else:
                job['Business Nature'] = 'Unknown'
        
        # Display processing statistics
        st.success(f"Categorized {total_companies} companies: {regex_matches} regex matches, {api_calls} AI calls")
        
        return jobs_data
