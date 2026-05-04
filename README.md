# 🚀 Intelligent Candidate Screening & Job Recommendation System

An AI-powered system that analyzes resumes, identifies skill gaps, and recommends relevant jobs using NLP, embeddings, and generative AI.

---

## 📌 Overview

This project is designed to simulate a **real-world recruitment intelligence system**.
It evaluates resumes against job descriptions, provides ATS-style scoring, and generates AI-powered insights to improve candidate profiles.

---

## ✨ Key Features

* 📄 **Resume Parsing** (PDF support)
* 🧠 **Skill Extraction & Normalization**
* 📊 **ATS-Based Resume Scoring**
* 🎯 **Job Matching System**
* 💡 **Skill Gap Analysis**
* 🤖 **AI Resume Improvement (Gemini)**
* 📈 **Dashboard & Analytics**
* 🧾 **PDF Report Generation**
* 🔐 **User Authentication System**

---

## 🧠 How It Works

1. Upload resume (PDF)
2. Paste job description
3. System extracts skills using NLP
4. Matches resume vs job using semantic similarity
5. Calculates ATS-style score
6. Identifies missing skills
7. Generates improved resume using AI
8. Recommends best-fit job roles

---

## 🏗️ Architecture

* **Frontend:** Streamlit
* **Backend Logic:** Python
* **NLP:** Sentence Transformers
* **AI:** Google Gemini API
* **Database:** SQLite
* **Visualization:** Plotly

---

## 📊 Scoring Logic

The system uses a hybrid scoring approach:

* Skill Match Score
* Semantic Similarity Score
* Missing Skill Penalty
* Resume Completeness

---

## 📁 Project Structure

```
job-recommendation-system/
│
├── app.py
├── database.py
├── requirements.txt
├── skill_list.csv
├── skill_suggestions.csv
├── jobs.csv
├── README.md
```

---

## 🚀 Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/job-recommendation-system.git
cd job-recommendation-system
```

---

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 3️⃣ Set Environment Variables

Create a `.env` file or set manually:

```env
GEMINI_API_KEY=your_api_key_here
```

---

### 4️⃣ Run the App

```bash
streamlit run app.py
```

---

## 🌐 Deployment

The application is deployed using **Streamlit Community Cloud**.

---

## 📸 Screenshots

*Add screenshots here (dashboard, resume output, analytics)*

---

## ⚠️ Limitations

* Depends on predefined skill datasets
* May not capture all domain-specific skills
* AI responses depend on external API quality

---

## 🔮 Future Improvements

* Skill weighting system
* Resume ranking across multiple candidates
* Fine-tuned domain-specific models
* Real-time job API integration

---

## 🎓 Academic Context

This project was developed as part of an **MSc Data Science Capstone Project**, focusing on real-world AI system design rather than isolated model training.

---

## 👨‍💻 Author

**Bharath K**
MSc Data Science

---

## ⭐ If you like this project

Give it a ⭐ on GitHub!

---
