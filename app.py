import streamlit as st
import base64
import plotly.express as px
import plotly.graph_objects as go
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib import colors
import io
import os
import pandas as pd
import bcrypt
import ast
import google.generativeai as genai 

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

gemini_model = genai.GenerativeModel("models/gemini-flash-latest")

@st.cache_data
def load_csv_data():
    skills_df = pd.read_csv("skill_list.csv")
    alias_df = pd.read_csv("aliases.csv")
    suggestions_df = pd.read_csv("skill_suggestions.csv")
    jobs_df = pd.read_csv("jobs.csv")

    return skills_df, alias_df, suggestions_df, jobs_df

def find_column(df, possible_names):
    for col in df.columns:
        if col.strip().lower() in possible_names:
            return col
    return None

skills_df, alias_df, suggestions_df, jobs_df = load_csv_data()

# Skills
skill_col = find_column(skills_df, ["skill", "skills"])

if skill_col is None:
    st.error(f"❌ skill_list.csv must contain column: skill")
    st.stop()

skills_list_flat = skills_df[skill_col].astype(str).str.lower().tolist()

# Aliases
alias_col = find_column(alias_df, ["alias"])
actual_col = find_column(alias_df, ["actual", "skill"])

if alias_col is None or actual_col is None:
    st.error("❌ aliases.csv must contain columns: alias, actual")
    st.stop()

skill_aliases = dict(
    zip(alias_df[alias_col].astype(str).str.lower(),
        alias_df[actual_col].astype(str).str.lower())
)

# Suggestions
skill_col_sug = find_column(suggestions_df, ["skill"])
suggestion_col = find_column(suggestions_df, ["suggestion", "description"])
link_col = find_column(suggestions_df, ["link", "url"])

if skill_col_sug is None or suggestion_col is None or link_col is None:
    st.error("❌ skill_suggestions.csv must contain: skill, suggestion, link")
    st.stop()

skill_suggestions = {}

for _, row in suggestions_df.iterrows():
    skill = str(row[skill_col_sug]).strip().lower()
    suggestion = str(row[suggestion_col]).strip()
    link = str(row[link_col]).strip()

    skill_suggestions[skill] = {
        "suggestion": suggestion,
        "link": link
    }

# Jobs
title_col = find_column(jobs_df, ["title", "job", "role"])
skills_col = find_column(jobs_df, ["skills", "skill"])

if title_col is None or skills_col is None:
    st.error("❌ jobs.csv must contain: title, skills")
    st.stop()

jobs = []
for _, row in jobs_df.iterrows():
    jobs.append({
        "title": str(row[title_col]),
        "skills": [s.strip().lower() for s in str(row[skills_col]).split(",")]
    })

st.set_page_config(
    page_title="AI Job Recommender",
    page_icon="🚀",
    layout="wide"
)


st.markdown("""
<style>

/* GLOBAL */
.stApp {
    background: radial-gradient(circle at top left, #1e293b, #020617);
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(10px);
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* GLASS CARD */
.glass {
    background: rgba(255,255,255,0.05);
    border-radius: 15px;
    padding: 20px;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    margin-bottom: 20px;
}

/* BUTTON */
.stButton>button {
    background: linear-gradient(135deg, #6366f1, #9333ea);
    border-radius: 12px;
    color: white;
    font-weight: 600;
    height: 3em;
    border: none;
}

/* INPUT */
.stTextInput input, textarea {
    border-radius: 10px !important;
    border: 1px solid #334155 !important;
    background-color: #020617 !important;
    color: white !important;
}

/* METRIC STYLE */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 10px;
    border: 1px solid rgba(255,255,255,0.05);
}
            
.skill-chip {
    display: inline-block;
    padding: 6px 12px;
    margin: 4px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
}

/* Resume skills */
.resume-chip {
    background: rgba(59,130,246,0.15);
    color: #60a5fa;
}

/* Job skills */
.job-chip {
    background: rgba(168,85,247,0.15);
    color: #c084fc;
}

/* Matched skills */
.match-chip {
    background: rgba(34,197,94,0.15);
    color: #4ade80;
}

/* Missing skills */
.miss-chip {
    background: rgba(239,68,68,0.15);
    color: #f87171;
}

/* TITLE */
h1, h2, h3 {
    color: #f1f5f9;
}

</style>
""", unsafe_allow_html=True)

from database import create_tables, connect_db
create_tables()

# ================= AUTH =================

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password, hashed):
    if isinstance(hashed, str):
        hashed = hashed.encode()   # 🔥 convert back to bytes
    return bcrypt.checkpw(password.encode(), hashed)

import re

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_strong_password(password):
    return len(password) >= 6


def register_user(email, password):
    conn = connect_db()
    cursor = conn.cursor()

    hashed = hash_password(password)

    try:
        cursor.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, hashed)
        )
        conn.commit()
        return True
    except:
        return False

    finally:
        conn.close()

def login_user(email, password):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, password FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    if user:
        user_id, stored_password = user

        if check_password(password, stored_password):
            return user_id

    return None

# ================= UTIL =================

def save_history(user_id, resume, job, final_score, semantic, skill, matched, missing):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO history 
        (user_id, resume, job, final_score, semantic_score, skill_score, matched_skills, missing_skills)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        resume,
        job,
        float(final_score),
        float(semantic),
        float(skill),
        str(matched),
        str(missing)
    ))

    conn.commit()
    conn.close()

def create_pdf(final_score, matched, missing, semantic, skill):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    section_style = styles["Heading2"]
    normal = styles["Normal"]

    content = []

    # ===== TITLE =====
    content.append(Paragraph("📄 Job Match Analysis Report", title_style))
    content.append(Spacer(1, 20))

    content.append(Paragraph("Generated by AI Resume Analyzer 🚀", normal))
    content.append(Spacer(1, 10))

    # ===== SCORE =====
    content.append(Paragraph("📊 Overall Score", section_style))
    content.append(Paragraph(f"<b>{final_score*100:.2f}%</b>", normal))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Semantic Score: {semantic*100:.2f}%", normal))
    content.append(Paragraph(f"Skill Match Score: {skill*100:.2f}%", normal))
    content.append(Spacer(1, 20))

    # ===== MATCHED =====
    content.append(Paragraph("✅ Matched Skills", section_style))
    if matched:
        for m in matched:
            content.append(Paragraph(f"• {m}", normal))
    else:
        content.append(Paragraph("No matched skills", normal))
    content.append(Spacer(1, 20))

    # ===== MISSING =====
    content.append(Paragraph("🚨 Missing Skills", section_style))
    if missing:
        for m in missing:
            content.append(Paragraph(f"• {m}", normal))
    else:
        content.append(Paragraph("No missing skills 🎉", normal))
    content.append(Spacer(1, 20))

    # ===== INSIGHT =====
    content.append(Paragraph("🧠 Insights", section_style))

    if final_score > 0.7:
        insight = "Strong match! You are well aligned with the job."
    elif final_score > 0.4:
        insight = "Moderate match. Improve key missing skills."
    else:
        insight = "Low match. Significant improvement needed."

    content.append(Paragraph(insight, normal))

    # ===== CHART =====
    drawing = Drawing(400, 200)

    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 50
    chart.height = 100
    chart.width = 300

    chart.data = [[semantic*100, skill*100, final_score*100]]
    chart.categoryAxis.categoryNames = ['Semantic', 'Skill', 'Final']

    chart.bars[0].fillColor = colors.blue

    drawing.add(chart)

    content.append(Paragraph("📊 Score Breakdown", section_style))
    content.append(Spacer(1, 10))
    content.append(drawing)
    content.append(Spacer(1, 20))

    # ===== BUILD =====
    doc.build(content)
    buffer.seek(0)

    return buffer


def create_resume_pdf(resume_text):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    title = styles["Heading1"]
    section = styles["Heading2"]
    normal = styles["Normal"]

    content = []

    # Split lines
    lines = resume_text.split("\n")

    for line in lines:
        line = line.strip()

        if not line:
            content.append(Spacer(1, 10))
            continue

    # Markdown headers
        if line.startswith("#"):
            clean = line.replace("#", "").strip()
            content.append(Paragraph(f"<b>{clean}</b>", section))

    # Bullet points
        elif line.startswith("-") or line.startswith("•"):
                content.append(Paragraph(line.replace("-", "•"), normal))

        else:
            content.append(Paragraph(line, normal))

        content.append(Spacer(1, 6))

    doc.build(content)
    buffer.seek(0)

    return buffer

def set_background(image_file):
    try:
        with open(image_file, "rb") as file:
            encoded = base64.b64encode(file.read()).decode()
    except FileNotFoundError:
        return  # silently skip if missing

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# ================= DATA =================



# ================= FUNCTIONS =================

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def generate_resume_from_jd(job_text):
    skills = extract_skills(job_text)

    summary = f"""
Motivated and detail-oriented professional with skills in {', '.join(skills[:5])}.
Passionate about building scalable applications and solving real-world problems.
"""

    skills_section = "\n".join([f"- {s}" for s in skills])

    projects = f"""
- Developed projects using {skills[0] if skills else "modern technologies"}
- Built applications demonstrating problem-solving and development skills
"""

    resume = f"""
===== GENERATED RESUME =====

SUMMARY:
{summary}

SKILLS:
{skills_section}

PROJECTS:
{projects}

EDUCATION:
Bachelor’s Degree in Computer Science (or relevant field)
"""

    return resume

def generate_resume_ai(job_text):
    try:
       prompt = f"""
       You are a TOP 1% professional resume writer.
 
       Rewrite a resume based on the job description.

       STRICT RULES:

       - NEVER use generic phrases (motivated, passionate, hardworking)
       - EVERY bullet must include measurable impact (% improvement, time saved, accuracy)
       - Use strong action verbs (Built, Optimized, Reduced, Designed)
       - Tailor EXACTLY to the job description
       - ATS optimized

       FORMAT STRICTLY:

       # PROFESSIONAL SUMMARY
       2-3 lines with ROLE + IMPACT

       # TECHNICAL SKILLS
       - Programming:
       - Tools:
       - Data:
       - Cloud:

       # PROJECT EXPERIENCE
       Include 2-3 projects:
       - Project Name
       - 2 bullet points with METRICS

       # EXPERIENCE
       Entry-level but IMPACTFUL

       # EDUCATION

       Job Description:
       {job_text}

       Return ONLY markdown.
       """

       response = gemini_model.generate_content(prompt) 
       return response.text if response and hasattr(response, "text") else "AI generation failed"
    

    except Exception as e:
        st.error(f"AI failed: {e}")   # 👈 ADD THIS
        return generate_resume_from_jd(job_text)


def extract_skills(text):
    text = text.lower()

    # Apply aliases safely
    for alias, actual in skill_aliases.items():
        text = re.sub(rf"\b{alias}\b", actual, text)

    found = set()

    for skill in skills_list_flat:
         if len(skill) > 2 and re.search(rf"\b{skill}\b", text):
            found.add(skill)

    return list(found) if found else ["general"]

def normalize_skills(skills):
    normalized = set()
    for s in skills:
        s = s.lower()
        if s in skill_aliases:
            normalized.add(skill_aliases[s])
        else:
            normalized.add(s)
    return normalized

# ================= MODEL =================

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

@st.cache_data
def get_embedding(text):
    return model.encode([text])


def calculate_score(similarity, skill_score, matched, missing, job_skills):

    # Base weighted score
    final = (0.6 * similarity) + (0.4 * skill_score)

    # Penalty for missing critical skills
    if len(job_skills) > 0:
        missing_ratio = len(missing) / len(job_skills)
        final -= missing_ratio * 0.2

    # Clamp
    return max(0, min(final, 1))

def match_resume_job(resume, job, resume_emb=None, resume_skills=None):

    if resume_emb is None:
        resume_emb = get_embedding(resume)

    if resume_skills is None:
        resume_skills = extract_skills(resume)

    job_emb = get_embedding("Job Description: " + job)

    similarity = cosine_similarity(resume_emb, job_emb)[0][0]

    job_skills = extract_skills(job)

    resume_set = normalize_skills(resume_skills)
    job_set = normalize_skills(job_skills)
    
    matched = list(resume_set & job_set)
    missing = list(job_set - resume_set)
    skill_score = len(matched) / (len(job_set) if job_set else 1)

    final_score = calculate_score(
        similarity,
        skill_score,
        matched,
        missing,
        job_skills
    )

    ats_score = min(1.0, (len(matched) / (len(job_set) if job_set else 1)) * 1.2)

    return {
        "final_score": round(final_score, 2),
        "semantic_score": round(similarity, 2),
        "skill_score": round(skill_score, 2),
        "ats_score": round(ats_score, 2),
        "matched_skills": matched,
        "missing_skills": missing,
        "top_missing": missing[:3]
    }
# ================= LOGIN =================

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.logged_in = False

st.sidebar.title("🔐 Login")

menu = st.sidebar.selectbox("Menu", ["Login", "Register"])
email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if menu == "Register":
    if st.sidebar.button("Register"):

        if not is_valid_email(email):
            st.sidebar.error("Invalid email format")

        elif not is_strong_password(password):
            st.sidebar.error("Password must be at least 6 characters")

        else:
            if register_user(email, password):
                st.sidebar.success("Registered!")
            else:
                st.sidebar.error("User already exists")

elif menu == "Login":
    if st.sidebar.button("Login"):

        if not is_valid_email(email):
            st.sidebar.error("Invalid email format")

        else:
            user = login_user(email, password)

            if user:
                st.session_state.user = user
                st.session_state.logged_in = True
                st.sidebar.success("Logged in!")
            else:
                st.sidebar.error("Invalid credentials")

# ================= MAIN APP =================

if st.session_state.get("logged_in"):
    st.success("Welcome back! 👋")

    if st.button("Logout"):
        st.session_state.clear()
        st.success("Logged out successfully")
        st.rerun()

    st.markdown("""
    <div class="glass">
    <h1 style="text-align:center;">🚀 AI Resume Analyzer</h1>
    <p style="text-align:center; color:#94a3b8;">
    Smart job matching powered by NLP + AI + Skill Intelligence
    </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<div class="glass">', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("📄 Upload Resume", type=["pdf"])
    job = st.text_area("🧾 Paste Job Description")
    if job:
        st.session_state.job = job

    mode = st.selectbox(
        "Resume Generation Mode",
        ["Standard (Offline)", "AI Enhanced"]
    )

    if st.button("🧠 Generate Resume from JD"):
        if job:

            with st.spinner("Generating resume..."):

                if mode == "AI Enhanced":
                    generated_resume = generate_resume_ai(job)
                else:
                    generated_resume = generate_resume_from_jd(job)

            st.markdown('<div class="glass">', unsafe_allow_html=True)
            st.markdown("### 📄 Generated Resume")
            st.markdown(generated_resume)
            st.markdown('</div>', unsafe_allow_html=True)

            resume_pdf = create_resume_pdf(generated_resume)

            st.download_button(
                "📄 Download Resume PDF",
                resume_pdf,
                file_name="generated_resume.pdf"
            )

        else:
            st.warning("Please enter job description first")

    if not uploaded_file and not job:
        st.markdown("""
        <div class="glass" style="text-align:center;">
        <h3>🚀 Start Your Analysis</h3>
        <p>Upload your resume and paste a job description to begin</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if not uploaded_file:
        st.info("📄 Upload your resume to begin")

    if not job:
        st.info("📝 Enter job description")

    resume = ""

    if uploaded_file:
        resume = extract_text_from_pdf(uploaded_file)
        st.session_state.resume = resume
        st.success("Resume uploaded successfully!")

    resume = st.session_state.get("resume", "")
    job = st.session_state.get("job", "")

    if st.button("🚀 Analyze Resume & Get Insights"):

        if resume:
            if not job:
                st.warning("Please enter a job description")
                st.stop()
            with st.spinner("🔍 Analyzing your resume..."):

                # 🔥 Generate ideal resume from JD (AI benchmark)
                ideal_resume = generate_resume_ai(job)
            
                resume_lower = resume.lower()
                job_lower = job.lower()

                resume_emb = get_embedding(resume_lower)
                st.session_state.resume_emb = resume_emb  
                resume_skills = extract_skills(resume_lower)

                data = match_resume_job(resume_lower, job_lower, resume_emb, resume_skills)
                ideal_data = match_resume_job(
                    ideal_resume.lower(),
                    job_lower
                )
                st.session_state.analysis_done = True
                st.session_state.data = data
                st.session_state.ideal_data = ideal_data
                st.session_state.ideal_resume = ideal_resume
        else:
            st.warning("Enter both Resume and Job")
        

                # 🔥 Analyze ideal resume
                

    if st.session_state.get("analysis_done"):

        data = st.session_state.data
        ideal_data = st.session_state.ideal_data
        ideal_resume = st.session_state.ideal_resume

        st.success("🎉 Analysis Complete!")
        st.balloons()

        st.markdown("### 🎯 Recommendation")

        if data["final_score"] > 0.7:
            st.success("You can confidently apply for this role.")
        elif data["final_score"] > 0.4:
            st.info("You are close — improve key skills before applying.")
        else:
            st.error("Improve your resume significantly before applying.")

        final_score = data["final_score"]
        similarity = data["semantic_score"]
        skill_score = data["skill_score"]
        matched = data["matched_skills"]
        missing = data["missing_skills"]

        top_missing = data.get("top_missing", missing[:3])

        resume_lower = st.session_state.get("resume", "").lower()
        job_lower = st.session_state.get("job", "").lower()

        resume_skills = extract_skills(resume_lower)
        job_skills = extract_skills(job_lower)

        left, right = st.columns([2, 1])

        with left:
            st.markdown("## 📊 Analysis Results")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("🎯 Final", f"{final_score*100:.1f}%")
            with col2:
                st.metric("🧠 Semantic", f"{similarity*100:.1f}%")
            with col3:
                st.metric("🧩 Skills", f"{skill_score*100:.1f}%")
            with col4:
                st.metric("📄 ATS", f"{data['ats_score']*100:.1f}%")

            st.progress(min(int(final_score * 100), 100))

            if final_score > 0.75:
                st.success("🟢 Strong Candidate")
            elif final_score > 0.5:
                st.info("🟡 Moderate Match")
            else:
                st.error("🔴 Needs Improvement")

        with right:
            st.markdown("### 🚀 Suggestions")

            if missing:
                for s in top_missing:
                    s_clean = s.strip().lower()

                    st.markdown(f"**{s}**")

                    info = skill_suggestions.get(s_clean)

                    if info:
                        st.caption(info["suggestion"])
                        st.markdown(f"[📚 Learn {s}]({info['link']})")
                    else:
                        st.caption("Improve this skill")
        st.markdown('</div>', unsafe_allow_html=True)

        st.caption("⚙️ Hybrid scoring (Semantic + Skill-based)")

            # ================= BENCHMARK =================

        st.markdown("## 🧠 Benchmark Comparison")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📄 Your Resume")
            st.metric("Score", f"{data['final_score']*100:.1f}%")

        with col2:
            st.markdown("### 🤖 Ideal Resume")
            st.metric("Score", f"{ideal_data['final_score']*100:.1f}%")

            # ================= GAP ANALYSIS =================

        st.markdown("## 🚨 Gap Analysis")
        user_skills_set = normalize_skills(resume_skills)
        ideal_skills_set = normalize_skills(extract_skills(ideal_resume))

        gap = ideal_skills_set - user_skills_set

        if gap:
            st.warning("You are missing key skills compared to ideal resume:")

            for g in list(gap)[:5]:
                st.markdown(f"- {g}")
        else:
            st.success("Your resume aligns well with the ideal profile!")


        st.markdown("## ✨ Auto Resume Improvement")

        if st.button("🚀 Improve My Resume"):
            improve_prompt = f"""
            You are an expert resume optimizer.

            Rewrite the resume to MATCH the job perfectly.

            Rules:
            - Add missing skills from JD
            - Add metrics (% improvement, speed, accuracy)
            - Use strong verbs (Built, Optimized, Reduced)
            - Remove weak phrases

            Job:
            {job}

            Resume:
            {resume}

            Make it look like a TOP 5% candidate.
            """
            try:
                response = gemini_model.generate_content(improve_prompt)
                improved = response.text if response and hasattr(response, "text") else "AI improvement failed"

                st.markdown("### 🔥 Improved Resume")
                st.markdown(improved)

            except Exception as e:
                st.error(f"AI failed: {e}")
            # ================= IMPROVEMENT METRIC =================

        st.markdown("## 📈 Improvement Potential")

        improvement = max(0, (ideal_data["final_score"] - data["final_score"]) * 100)

        if improvement > 40:
            st.error(f"🚨 High improvement needed: {improvement:.1f}%")
        elif improvement > 20:
            st.warning(f"⚡ Moderate improvement: {improvement:.1f}%")
        elif improvement > 0:
            st.info(f"✅ Minor improvement: {improvement:.1f}%")
        else:
            st.success("🔥 Already optimized")


        st.markdown("## 🧠 AI Insight")

        insight_prompt = f"""
        You are a senior hiring manager.

        Analyze the candidate resume vs job description.

        Give:

        1. Strengths (based on JD match)
        2. Weaknesses (missing critical skills)
        3. Specific improvements (what EXACTLY to add/change)

        Keep it concise and professional.

        Job:
        {job}

        Resume:
        {resume[:1500]}
        Provide actionable feedback to improve this resume for the given job.
        """

        try:
            response = gemini_model.generate_content(insight_prompt)
            improved = response.text if response and hasattr(response, "text") else "AI insight failed"
            st.markdown(improved)

        except Exception as e:
            st.error(f"AI insight failed: {e}")

            # ================= IDEAL RESUME VIEW =================

        with st.expander("📄 View Ideal Resume (AI Generated Benchmark)"):
            st.markdown(ideal_resume)



        st.markdown("## 📊 Score Comparison")

        compare_df = pd.DataFrame({
            "Category": ["Your Resume", "Ideal Resume"],
            "Score": [data["final_score"]*100, ideal_data["final_score"]*100]
        })

        fig_compare = px.bar(
            compare_df,
            x="Category",
            y="Score",
            text="Score",
            title="Your vs Ideal Resume Score"
        )

        fig_compare.update_traces(texttemplate='%{text:.1f}%', textposition='outside')

        st.plotly_chart(fig_compare, use_container_width=True)

        st.markdown("## 📈 Improvement Gauge")

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=improvement,
            title={'text': "Improvement Potential (%)"},
                gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "green"},
            }
        ))

        st.plotly_chart(fig_gauge, use_container_width=True)


        st.markdown("## 🎯 Skill Gap Visualization")

        gap_list = list(gap)[:5]

        if gap_list:
            gap_df = pd.DataFrame({
                "Skill": gap_list,
                "Missing": [1]*len(gap_list)
            })

            fig_gap = px.bar(
                gap_df,
                x="Skill",
                y="Missing",
                title="Top Missing Skills"
            )

            st.plotly_chart(fig_gap, use_container_width=True)
        else:
            st.success("No major skill gaps 🎉")

        user_id = st.session_state.user
        save_history(
            user_id,
            resume[:1000],
            job,
            final_score,
            similarity,
            skill_score,
            matched,
            missing
        )


        st.subheader("🎯 Skill Match Radar")

        labels = ["Semantic", "Skill", "Final"]

        values = [ 
            similarity,
            skill_score,
            final_score
        ]

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=labels,
            fill='toself'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0,1])
            ),
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # Skills
        # ================= PREMIUM SKILL UI =================

        st.markdown("### 🧠 Resume Skills")
        st.markdown(
            "".join([f"<span class='skill-chip resume-chip'>{s}</span>" for s in resume_skills]),
            unsafe_allow_html=True
        )

        st.markdown("### 💼 Job Skills")
        st.markdown(
            "".join([f"<span class='skill-chip job-chip'>{s}</span>" for s in job_skills]),
            unsafe_allow_html=True
        )

        with st.expander("📄 Detailed Skill Analysis"):

            st.markdown("### ✅ Matched Skills")
            st.markdown(
                "".join([f"<span class='skill-chip match-chip'>{s}</span>" for s in matched]),
                unsafe_allow_html=True
            )

            st.markdown("### 🚨 Missing Skills")
            st.markdown(
                "".join([f"<span class='skill-chip miss-chip'>{s}</span>" for s in missing]),
                unsafe_allow_html=True
            )

        if len(missing) > 5:
            st.warning("🚨 You are missing several key skills for this role")
        elif len(missing) > 2:
            st.info("⚡ You are close! Improve a few important skills")
        else:
            st.success("🔥 Strong match! Only minor improvements needed")

        # Job matching
        st.markdown("---")

        resume_emb = st.session_state.get("resume_emb")

        scores = []

        for j in jobs:
            job_text = f"""
            Role: {j['title']}
            Skills: {', '.join(j['skills'])}
            """

            data_temp = match_resume_job(resume_lower, job_text, resume_emb, resume_skills)
            score = (data_temp["final_score"] * 0.7) + (data_temp["skill_score"] * 0.3)

            scores.append((j["title"], score)) 
        scores.sort(key=lambda x: x[1], reverse=True)

        st.subheader("🏆 Top Job Matches")

        for job_title, s in scores[:3]:
            st.markdown(f"""
            <div class="glass">
                <h3>💼 {job_title}</h3>
                <p>Match Score: <b>{s*100:.1f}%</b></p>
            </div>
            """, unsafe_allow_html=True)

            st.progress(float(s))
        
            for j in jobs:
                if j["title"] == job_title:
                    common = set(resume_skills) & set(j["skills"])
                    if common:
                        st.caption(f"Matched skills: {', '.join(list(common)[:3])}")
                    break

            # PDF
        pdf = create_pdf(
            final_score,
            matched,
            missing,
            similarity,
            skill_score
        )

        st.download_button("Download Professional Report", pdf, "report.pdf")            

        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ===== 📊 ADD HISTORY BLOCK HERE =====
    st.markdown("---")
    st.subheader("📊 Your Past Analyses")
    st.markdown('<div class="glass">', unsafe_allow_html=True)

    conn = connect_db()
    cursor = conn.cursor()

    user_id = st.session_state.user

    cursor.execute("""
        SELECT resume, job, final_score, semantic_score, skill_score, matched_skills, missing_skills, created_at
        FROM history
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()

    from collections import Counter

    all_missing = []

    for r in rows:
        try:
            missing_list = ast.literal_eval(r[6]) if len(r) > 6 else []
            all_missing.extend(missing_list)
        except:
            continue

    top_gaps = list(set(all_missing))[:5]
    conn.close()

    rows = rows[:9]   


    for r in rows:
        try:
            score = float(r[2])
        except:
            continue   # skip corrupted row

        st.markdown(f"### 🧠 Score: {score:.2f}")
        st.caption(f"⏱ {r[7]}")
        st.write(f"📄 {r[1][:120]}...")
        st.markdown("---")

    st.markdown('</div>', unsafe_allow_html=True)

        
    st.subheader("📊 Analytics Dashboard")

    if rows:
    
        df = pd.DataFrame(
           rows,
           columns=[
               "resume",
               "job",
               "score",
               "semantic_score",
               "skill_score",
               "matched_skills",
               "missing_skills",
               "time"
            ]
        )
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        df = df.dropna(subset=["score"])
        df["time"] = pd.to_datetime(df["time"])

        st.write("### 📅 Filter by Date")

        min_date = df["time"].min().date() if not df.empty else None
        max_date = df["time"].max().date() if not df.empty else None

        start_date = st.date_input(
            "Start Date",
            min_date,
            key="start_date"
        )

        end_date = st.date_input(
           "End Date",
            max_date,
            key="end_date"
        )

        df_filtered = df[
           (df["time"].dt.date >= start_date) &
           (df["time"].dt.date <= end_date)
        ]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("🧾 Total Runs", len(df_filtered))

        with col2:
            st.metric("📈 Avg Score", f"{df_filtered['score'].mean():.2f}")

        with col3:
            st.metric("🏆 Best Score", f"{df_filtered['score'].max():.2f}")

# ================= WORST SCORE =================
        with col4:
            st.metric("📉 Worst Score", f"{df_filtered['score'].min():.2f}")

# ================= TREND =================
        st.subheader("📈 Performance Trend")

        df_sorted = df_filtered.sort_values("time")
        st.line_chart(df_sorted.set_index("time")["score"])

# ================= DISTRIBUTION =================
        st.write("### 📉 Score Distribution")
        st.bar_chart(df_filtered["score"])

# ================= INSIGHTS =================
        st.subheader("🧠 Insights")

        if not df_filtered.empty:

    # Trend insight
            if len(df_filtered) > 1:
                if df_filtered["score"].iloc[-1] > df_filtered["score"].iloc[0]:
                    st.success("📈 Your performance is improving over time!")
                else:
                    st.warning("📉 Your scores are fluctuating — improve missing skills.")

    # Overall performance insight
            if df_filtered["score"].mean() > 0.7:
                st.success("🔥 Strong profile overall!")
            elif df_filtered["score"].mean() > 0.4:
                st.info("⚡ Moderate performance — room to improve.")
            else:
               st.error("🚨 Low match scores — focus on key skills.")


        else:
            st.info("Not enough data for insights")

    st.subheader("🚨 Your Top Skill Gaps")

    if top_gaps:
        for skill in top_gaps:
            st.write(f"{skill}")
    else:
        st.info("No major skill gaps detected yet")
      
    
else:
    st.warning("🔐 Please login to continue")

st.markdown("---")
st.caption("🚀 Built with AI | Intelligent Candidate Screening System")