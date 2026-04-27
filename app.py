import streamlit as st
st.set_page_config(layout="wide")
import base64
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
import pandas as pd
import bcrypt
import ast

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
        (user_id, resume, job, similarity, semantic_score, skill_score, matched_skills, missing_skills)
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

skills_list = {

"programming": [
"python","java","c","c++","c#","go","rust","kotlin","swift","typescript","javascript","r","matlab","scala","perl"
],

"web_frontend": [
"html","css","sass","less","bootstrap","tailwind",
"react","angular","vue","next.js","nuxt.js","redux","webpack","vite"
],

"web_backend": [
"node.js","express","django","flask","fastapi","spring","spring boot",
"laravel","ruby on rails","asp.net","rest api","graphql","microservices"
],

"databases": [
"sql","mysql","postgresql","mongodb","redis","cassandra","firebase",
"oracle","sqlite","dynamodb","neo4j","elasticsearch"
],

"data_ai": [
"machine learning","deep learning","nlp","computer vision",
"data science","pandas","numpy","scikit-learn","matplotlib","seaborn",
"tensorflow","pytorch","keras","xgboost","lightgbm","statsmodels"
],

"cloud_devops": [
"aws","azure","gcp","docker","kubernetes","jenkins","github actions",
"terraform","ansible","linux","bash","shell scripting","ci/cd"
],

"mobile": [
"android","ios","react native","flutter","dart","swift ui","kotlin multiplatform"
],

"testing": [
"unit testing","integration testing","pytest","selenium","cypress","jest","mocha"
],

"big_data": [
"hadoop","spark","kafka","hive","airflow","flink","databricks"
],

"security": [
"penetration testing","ethical hacking","network security","cryptography",
"owasp","vulnerability assessment"
],

"tools": [
"git","github","gitlab","jira","figma","postman","tableau","power bi","notion"
],

"soft_skills": [
"communication","teamwork","problem solving","leadership",
"time management","critical thinking","adaptability"
]

}

skills_list_flat = [s for category in skills_list.values() for s in category]


skill_aliases = {

# Programming
"py":"python",
"js":"javascript",
"ts":"typescript",

# AI
"ml":"machine learning",
"dl":"deep learning",
"ai":"machine learning",

# Frameworks
"reactjs":"react",
"nextjs":"next.js",
"node":"node.js",
"expressjs":"express",
"springboot":"spring boot",

# Data
"sklearn":"scikit-learn",
"tf":"tensorflow",

# Cloud
"aws cloud":"aws",
"google cloud":"gcp",

# Databases
"postgres":"postgresql",
"mongo":"mongodb",
"nosql":"mongodb",

# DevOps
"ci cd":"ci/cd",

# NLP
"natural language processing":"nlp",
"structured query language":"sql",
"mysql db":"mysql",
"postgres db":"postgresql",

"mongo db":"mongodb",
"nosql database":"mongodb",

"firebase realtime db":"firebase",
"machine learning models":"machine learning",
"ml models":"machine learning",

"deep neural networks":"deep learning",
"neural networks":"deep learning",

"text processing":"nlp",
"language models":"nlp",

"data analysis":"data science",
"data analytics":"data science",

"pandas library":"pandas",
"numpy library":"numpy",
"amazon web services":"aws",
"aws ec2":"aws",
"aws s3":"aws",

"google cloud platform":"gcp",

"docker containers":"docker",
"containerization":"docker",

"container orchestration":"kubernetes",
"k8s":"kubernetes",

"continuous integration":"ci/cd",
"continuous deployment":"ci/cd",

"linux os":"linux",
"unix":"linux",
}

skill_suggestions = {

# Programming
"python":"Build automation scripts, APIs, and data projects",
"java":"Practice OOP concepts and backend systems",
"c++":"Focus on data structures and system-level programming",
"c":"Learn memory management and embedded basics",
"javascript":"Master async programming and DOM manipulation",
"typescript":"Learn type safety and scalable frontend apps",
"go":"Build high-performance backend services",
"rust":"Learn safe systems programming and performance optimization",

# Web Frontend
"html":"Create semantic and accessible web pages",
"css":"Practice responsive design and layouts",
"sass":"Learn modular CSS and variables",
"bootstrap":"Build responsive UI quickly",
"tailwind":"Design modern UI using utility classes",
"react":"Build dynamic apps using hooks and state",
"angular":"Learn component-based frontend architecture",
"vue":"Build reactive interfaces with Vue ecosystem",
"next.js":"Learn SSR and performance optimization",

# Backend
"node.js":"Build scalable backend APIs",
"express":"Create REST APIs and middleware",
"django":"Develop secure full-stack web apps",
"flask":"Build lightweight APIs and services",
"fastapi":"Create high-performance APIs with Python",
"spring":"Develop enterprise Java applications",
"spring boot":"Build microservices with ease",
"graphql":"Learn flexible API querying",
"microservices":"Understand distributed system design",

# Databases
"sql":"Practice joins, indexing, and optimization",
"mysql":"Work on relational database design",
"postgresql":"Learn advanced SQL and performance tuning",
"mongodb":"Build NoSQL-based applications",
"redis":"Use caching for performance improvement",
"cassandra":"Handle large-scale distributed data",
"firebase":"Build real-time apps with backend-as-a-service",
"sqlite":"Use lightweight databases for apps",

# Data Science & AI
"machine learning":"Work on real datasets and model building",
"deep learning":"Study neural networks and CNNs",
"nlp":"Build chatbots and text processing apps",
"computer vision":"Work on image recognition projects",
"data science":"Analyze and visualize real-world data",
"pandas":"Manipulate and analyze datasets efficiently",
"numpy":"Work with numerical computations",
"scikit-learn":"Build ML models quickly",
"matplotlib":"Visualize data insights",
"seaborn":"Create advanced statistical plots",
"tensorflow":"Build deep learning models",
"pytorch":"Develop flexible neural networks",
"xgboost":"Improve model performance",
"lightgbm":"Handle large-scale ML efficiently",

# DevOps & Cloud
"aws":"Deploy scalable applications in cloud",
"azure":"Work on Microsoft cloud services",
"gcp":"Use Google cloud for data and apps",
"docker":"Learn containerization and deployment",
"kubernetes":"Manage container orchestration",
"jenkins":"Automate CI/CD pipelines",
"github actions":"Automate workflows and deployments",
"terraform":"Manage infrastructure as code",
"ansible":"Automate configuration management",
"linux":"Master command line and server handling",
"bash":"Write shell scripts for automation",
"ci/cd":"Implement automated deployment pipelines",

# Mobile
"android":"Build native Android applications",
"ios":"Develop apps for Apple devices",
"react native":"Create cross-platform mobile apps",
"flutter":"Build fast UI apps with Dart",
"dart":"Learn Flutter app development",
"swift ui":"Design modern iOS interfaces",

# Testing
"unit testing":"Write tests for code reliability",
"pytest":"Test Python applications effectively",
"selenium":"Automate browser testing",
"cypress":"Perform frontend testing",
"jest":"Test JavaScript applications",
"mocha":"Run backend JS testing",

# Big Data
"hadoop":"Handle distributed data processing",
"spark":"Process large datasets efficiently",
"kafka":"Build real-time data pipelines",
"hive":"Query big data using SQL-like language",
"airflow":"Manage data workflows",
"flink":"Stream data processing",

# Security
"penetration testing":"Practice ethical hacking techniques",
"ethical hacking":"Learn vulnerability detection",
"network security":"Secure systems and networks",
"cryptography":"Understand encryption techniques",
"owasp":"Learn web security standards",

# Tools
"git":"Use version control effectively",
"github":"Collaborate on projects",
"gitlab":"Manage CI/CD pipelines",
"jira":"Track tasks and agile workflows",
"figma":"Design UI/UX prototypes",
"postman":"Test APIs efficiently",
"tableau":"Create data dashboards",
"power bi":"Visualize business data",

# Soft Skills
"communication":"Improve clarity in technical discussions",
"teamwork":"Collaborate effectively in projects",
"problem solving":"Practice coding challenges",
"leadership":"Lead teams and decision-making",
"time management":"Manage deadlines efficiently",
"critical thinking":"Analyze problems logically",
"adaptability":"Learn new technologies quickly"
}


jobs = [

{"title":"Machine Learning Engineer","skills":["python","machine learning","tensorflow","pytorch","sql"]},
{"title":"Data Scientist","skills":["python","data science","machine learning","pandas","numpy"]},
{"title":"AI Engineer","skills":["python","deep learning","nlp","tensorflow","pytorch"]},

{"title":"Frontend Developer","skills":["javascript","react","html","css","typescript"]},
{"title":"React Developer","skills":["react","javascript","redux","html","css"]},
{"title":"Angular Developer","skills":["angular","typescript","html","css"]},

{"title":"Backend Developer","skills":["python","django","flask","sql","rest api"]},
{"title":"Node.js Developer","skills":["node.js","express","mongodb","rest api"]},
{"title":"Java Developer","skills":["java","spring","spring boot","sql"]},

{"title":"Full Stack Developer","skills":["javascript","react","node.js","mongodb","html","css"]},

{"title":"DevOps Engineer","skills":["docker","kubernetes","aws","jenkins","linux"]},
{"title":"Cloud Engineer","skills":["aws","azure","gcp","terraform"]},

{"title":"Mobile App Developer","skills":["flutter","dart","android","ios"]},
{"title":"Android Developer","skills":["android","kotlin","java"]},
{"title":"iOS Developer","skills":["ios","swift","swift ui"]},

{"title":"Data Analyst","skills":["sql","excel","python","power bi"]},
{"title":"Business Analyst","skills":["sql","excel","communication"]},

{"title":"Cybersecurity Analyst","skills":["network security","penetration testing","cryptography"]},
{"title":"Ethical Hacker","skills":["ethical hacking","penetration testing","owasp"]},

{"title":"Big Data Engineer","skills":["spark","hadoop","kafka"]},
{"title":"Data Engineer","skills":["python","sql","etl","airflow"]},

{"title":"QA Engineer","skills":["testing","selenium","pytest"]},
{"title":"Automation Tester","skills":["selenium","cypress","pytest"]},

{"title":"System Administrator","skills":["linux","bash","networking"]},
{"title":"Site Reliability Engineer","skills":["linux","docker","kubernetes","ci/cd"]},

{"title":"Game Developer","skills":["c++","unity","unreal engine"]},
{"title":"Embedded Systems Engineer","skills":["c","c++","microcontrollers"]},

{"title":"UI/UX Designer","skills":["figma","design","user research"]},

{"title":"Blockchain Developer","skills":["solidity","ethereum","web3"]},
{"title":"AR/VR Developer","skills":["unity","c#","vr"]},

{"title":"Software Engineer","skills":["java","python","data structures","algorithms"]},
{"title":"Senior Software Engineer","skills":["system design","microservices","scalability"]},

{"title":"Product Manager","skills":["communication","roadmap","agile"]},
{"title":"Technical Lead","skills":["leadership","architecture","scalability"]},

{"title":"MLOps Engineer","skills":["python","mlops","docker","kubernetes","ci/cd"]},

{"title":"Prompt Engineer","skills":["llm","prompt engineering","nlp","gpt"]},

{"title":"AI Research Engineer","skills":["deep learning","transformers","pytorch","research"]},

{"title":"Platform Engineer","skills":["kubernetes","terraform","cloud","devops"]},

{"title":"API Developer","skills":["rest api","graphql","node.js","fastapi"]},

{"title":"Security Engineer","skills":["network security","siem","incident response"]},

{"title":"Data Platform Engineer","skills":["spark","kafka","airflow","data pipelines"]},

{"title":"Cloud Architect","skills":["aws","azure","architecture","scalability"]},

{"title":"Frontend Architect","skills":["react","architecture","performance"]},

{"title":"Backend Architect","skills":["microservices","system design","scalability"]}

]

# ================= FUNCTIONS =================

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_skills(text):
    text = text.lower()
    found = set()

    # Check direct skills
    for skill in skills_list_flat:
        if skill in text:
            found.add(skill)

    # Check aliases
    for alias, actual in skill_aliases.items():
        if alias in text:
            found.add(actual)

    return list(found) if found else ["general"]

# ================= MODEL =================

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

@st.cache_data
def get_embedding(text):
    return model.encode([text])


def calculate_score(similarity, skill_score, matched, missing, job_skills):
    penalty = 0

    critical_skills = job_skills[:2]
    for skill in critical_skills:
        if skill in missing:
            penalty += 0.1

    bonus = 0
    if len(matched) > len(job_skills) * 0.7:
        bonus = 0.05

    final = (0.6 * similarity) + (0.4 * skill_score) + bonus - penalty

    return max(0, min(final, 1))


def match_resume_job(resume, job):

    resume_emb = get_embedding(resume)
    job_emb = get_embedding(job)

    similarity = cosine_similarity(resume_emb, job_emb)[0][0]

    resume_skills = extract_skills(resume)
    job_skills = extract_skills(job)

    matched = list(set(resume_skills) & set(job_skills))
    missing = [s for s in job_skills if s not in resume_skills]

    skill_score = len(matched) / (len(job_skills) if job_skills else 1)

    final_score = calculate_score(
        similarity,
        skill_score,
        matched,
        missing,
        job_skills
    )

    return {
        "final_score": round(final_score, 2),
        "semantic_score": round(similarity, 2),
        "skill_score": round(skill_score, 2),
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

    set_background("better.png")

    if st.button("Logout"):
        st.session_state.clear()
        st.success("Logged out successfully")
        st.rerun()

    st.markdown("""
    # 🤖 Intelligent Candidate Screening System
    ### AI-powered Resume Analyzer & Job Matcher
    """)
    st.markdown("---")

    uploaded_file = st.file_uploader("Upload Resume", type=["pdf"])
    job = st.text_area("Enter Job Description")

    if not uploaded_file:
        st.info("📄 Upload your resume to begin")

    if not job:
        st.info("📝 Enter job description")

    resume = ""

    if uploaded_file:
        resume = extract_text_from_pdf(uploaded_file)
        st.success("Resume uploaded!")

    if st.button("Match"):

        if resume and job:

            resume_lower = resume.lower()
            job_lower = job.lower()

            resume_emb = get_embedding(resume_lower)
            data = match_resume_job(resume_lower, job_lower)


            final_score = data["final_score"]
            similarity = data["semantic_score"]
            skill_score = data["skill_score"]
            matched = data["matched_skills"]
            missing = data["missing_skills"]

            resume_skills = matched
            job_skills = matched + missing

            st.subheader("📊 Why this score?")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("🎯 Final Score", f"{float(final_score)*100:.1f}%")

            with col2:
                st.metric("🧠 Semantic", f"{float(similarity)*100:.1f}%")

            with col3:
                st.metric("🧩 Skills", f"{float(skill_score)*100:.1f}%")

            st.info(
                "Final score is calculated as: 60% semantic similarity + 40% skill match"
            )

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

            st.subheader(f"Final Score: {final_score:.2f}")
            st.write(f"Semantic: {similarity:.2f} | Skill: {skill_score:.2f}")
            st.progress(int(final_score * 100))

            st.subheader("📊 Score Visualization")

            chart_data = pd.DataFrame({
                "Scores": [similarity, skill_score, final_score]
            }, index=["Semantic", "Skill", "Final"])

            st.bar_chart(chart_data)
            st.markdown("---")  

            # Skills
            st.write("Resume Skills:", resume_skills)
            st.write("Job Skills:", job_skills)

            top_missing = data.get("top_missing", missing[:3])

            with st.expander("📄 Detailed Skill Analysis"):

                st.subheader("✅ Matched Skills")
                for skill in matched:
                    st.success(f"✔ {skill}")

                st.subheader("🚨 Missing Skills")
                for skill in missing:
                    st.error(f"✖ {skill}")

            if len(missing) > 5:
                st.warning("🚨 You are missing several key skills for this role")
            elif len(missing) > 2:
                st.info("⚡ You are close! Improve a few important skills")
            else:
                st.success("🔥 Strong match! Only minor improvements needed")

            # Suggestions
            st.subheader("🚀 Suggestions")
            if missing:

                for s in top_missing:
                    st.markdown(f"### {s}")
                    st.caption(skill_suggestions.get(s, "Learn this skill with projects"))
            else:
                st.success("🎉 You already match all required skills!")

            # Job matching
            st.markdown("---")
            st.subheader("Top Jobs")

            scores = []
            
            for j in jobs:
                job_text = j["title"] + " " + " ".join(j["skills"])
    
                job_emb_temp = get_embedding(job_text)
                semantic_score = cosine_similarity(resume_emb, job_emb_temp)[0][0]

                job_skills_temp = j["skills"]

                matched_temp = len(set(resume_skills) & set(job_skills_temp))
                total_temp = len(job_skills_temp) if job_skills_temp else 1

                skill_score_temp = matched_temp / total_temp

                score = 0.6 * semantic_score + 0.4 * skill_score_temp
                scores.append((j["title"], score))
                
            scores.sort(key=lambda x: x[1], reverse=True) 

            st.subheader("🏆 Top Job Matches")

            for j, s in scores[:3]:
                st.markdown(f"""
                ### 💼 {j}
                Match Score: **{s*100:.1f}%**
                """)
                st.progress(float(s))
                st.markdown("---")

            # PDF
            pdf = create_pdf(
                final_score,
                matched,
                missing,
                similarity,
                skill_score
            )

            st.download_button("Download Report", pdf, "report.pdf")

        else:
            st.warning("Enter both Resume and Job")
        
    # ===== 📊 ADD HISTORY BLOCK HERE =====
    st.markdown("---")
    st.subheader("📊 Your Past Analyses")

    conn = connect_db()
    cursor = conn.cursor()

    user_id = st.session_state.user

    cursor.execute("""
        SELECT resume, job, similarity, semantic_score, skill_score, matched_skills, missing_skills, created_at
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

    top_gaps = Counter(all_missing).most_common(5)
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
        for skill, count in top_gaps:
            st.write(f"{skill} → missing {count} times")
    else:
        st.info("No major skill gaps detected yet")
      
    
else:
    st.warning("🔐 Please login to continue")

st.markdown("---")
st.caption("🚀 Built with AI | Intelligent Candidate Screening System")