import json
import tempfile

import streamlit as st

from groq_parser import refine_with_groq
from groq_confidence import calculate_confidence_scores
from resume_parser import build_resume_json


st.set_page_config(page_title="AI Resume Parser", layout="wide", page_icon="🤖")

st.title("🤖 AI Resume Parser")
st.write("Upload a PDF resume and extract structured data with AI-powered analysis.")

uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

if uploaded_file is not None:
    # Write uploaded bytes to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name
    
    st.success("✅ Resume uploaded successfully!")
    
    # Create two columns for buttons
    col1, col2 = st.columns(2)
    
    with col1:
        parse_button = st.button("📄 Parse Resume", use_container_width=True, type="primary")
    
    with col2:
        confidence_button = st.button("📊 Calculate Confidence Scores", use_container_width=True)
    
    # Parse Resume Button
    if parse_button:
        with st.spinner("Extracting and parsing resume..."):
            # Stage 1: Extract with PyMuPDF
            initial_json = build_resume_json(tmp_path)
            
            # Stage 2: Refine with Groq AI
            result = refine_with_groq(initial_json)
            
            # Store in session state
            st.session_state['resume_data'] = result
        
        st.success("✅ Resume parsed successfully!")
        st.subheader("📄 Structured Resume JSON")
        st.json(result)
        
        # Download button
        st.download_button(
            label="⬇️ Download Resume JSON",
            data=json.dumps(result, indent=2),
            file_name=f"{result.get('name', 'resume').replace(' ', '_')}_data.json",
            mime="application/json",
        )
    
    # Confidence Score Button
    if confidence_button:
        # Check if resume data exists
        if 'resume_data' not in st.session_state:
            with st.spinner("Parsing resume first..."):
                initial_json = build_resume_json(tmp_path)
                result = refine_with_groq(initial_json)
                st.session_state['resume_data'] = result
        
        with st.spinner("Calculating skill confidence scores..."):
            confidence_scores = calculate_confidence_scores(st.session_state['resume_data'])
        
        if not confidence_scores:
            confidence_scores = {}
        
        st.success("✅ Confidence scores calculated successfully!")
        st.subheader("📊 Skill Confidence Scores")
        st.json(confidence_scores)
        
        # Download button
        st.download_button(
            label="⬇️ Download Confidence Scores JSON",
            data=json.dumps(confidence_scores, indent=2),
            file_name=f"{st.session_state['resume_data'].get('name', 'resume').replace(' ', '_')}_confidence.json",
            mime="application/json",
        )


