from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
def calculate_score(similarity, skill_score, matched, missing, job_skills):
    penalty = 0

    critical_skills = job_skills[:2]
    for skill in critical_skills:
        if skill in missing:
            penalty += 0.1

    bonus = 0
    if len(matched) > len(job_skills) * 0.7:
        bonus = 0.05

    final = (0.5 * similarity) + (0.4 * skill_score) + bonus - penalty

    return max(0, min(final, 1)), penalty, bonus 

app = FastAPI()

# Load model once
@app.on_event("startup")
def load_model():
    global model
    model = SentenceTransformer('all-MiniLM-L6-v2')

# Input schema
class MatchRequest(BaseModel):
    resume: str
    job: str


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

def extract_skills(text):
    text = text.lower()
    found = set()

    for skill in skills_list_flat:
        if skill in text:
            found.add(skill)

    for alias, actual in skill_aliases.items():
        if alias in text:
            found.add(actual)

    return list(found) if found else ["general"]

@app.post("/match")
def match(req: MatchRequest):

    resume = req.resume.lower()
    job = req.job.lower()

    # embeddings
    resume_emb = model.encode([resume])
    job_emb = model.encode([job])

    similarity = cosine_similarity(resume_emb, job_emb)[0][0]
    

    # skills
    resume_skills = extract_skills(resume)
    job_skills = extract_skills(job)

    matched = list(set(resume_skills) & set(job_skills))
    missing = [s for s in job_skills if s not in resume_skills]

    skill_score = len(matched) / (len(job_skills) if job_skills else 1)

    final_score, penalty, bonus = calculate_score(
        similarity,
        skill_score,
        matched,
        missing,
        job_skills
    )

    return {
       "final_score": float(round(final_score, 2)),
       "semantic_score": float(round(similarity, 2)),
       "skill_score": float(round(skill_score, 2)),
       "matched_skills": matched,
       "missing_skills": missing,
       "top_missing": missing[:3],
       "explanation": {
           "penalty": penalty,
           "bonus": bonus
        }
    }
    