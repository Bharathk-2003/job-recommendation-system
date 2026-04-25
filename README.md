# 🚀 Intelligent Candidate Screening & Job Recommendation System

A smart system that analyzes resumes and recommends relevant jobs using **NLP + semantic similarity + skill matching**.

---

## 🔥 Features

* 📄 Resume parsing (PDF support)
* 🤖 Semantic similarity using Sentence Transformers
* 🧠 Skill-based matching
* 📊 Scoring system (semantic + skill score)
* 📈 Analytics dashboard (Streamlit)
* ⚡ FastAPI backend for API endpoints
* 🔐 (Optional) Authentication system

---

## 🛠️ Tech Stack

* Python
* FastAPI
* Streamlit
* Sentence Transformers
* Scikit-learn
* Pandas
* SQLite
* PyPDF2 / ReportLab

---

## 📂 Project Structure

```
job-recommendation-system/
│
├── app.py              # Streamlit UI
├── api.py              # FastAPI backend
├── database.py         # Database logic
├── requirements.txt
├── projyA.db
├── better.png          # UI preview
└── .gitignore
```

---

## ⚙️ Installation

```bash
git clone https://github.com/your-username/job-recommendation-system.git
cd job-recommendation-system
pip install -r requirements.txt
```

---

## ▶️ Run the App

### Run Streamlit UI

```bash
streamlit run app.py
```

### Run FastAPI backend

```bash
uvicorn api:app --reload
```

---

## 📊 How It Works

1. Upload resume (PDF)
2. Extract text
3. Compare with job descriptions
4. Calculate:

   * Semantic similarity
   * Skill match score
5. Recommend best jobs

---

## 📸 Demo

(Add your screenshot here 👇)

![App Screenshot](better.png)

---

## 📌 Future Improvements (Phase 2)

* User login system
* Dashboard analytics
* Multi-job recommendations
* Better ranking algorithm
* Deployment (Streamlit Cloud / Render)

---

## 👨‍💻 Author

Bharath
GitHub: https://github.com/Bharathk-2003

---

## ⭐ If you like this project

Give it a star ⭐ on GitHub!
