# JobAgent AI 🤖

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Render](https://img.shields.io/badge/Render-Deploy%20Ready-46E3B7.svg?style=flat&logo=render&logoColor=white)](https://render.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **JobAgent AI** is an autonomous, human-like multi-agent system designed to search, score, tailor, apply to, and track **Data Science, Machine Learning, and AI Engineering** internships and entry-level positions across **LinkedIn, Internshala, Naukri, Indeed, and Wellfound (AngelList)**.

Built with a conversational career coach persona (**Alex**), bidirectional audio/voice interaction, a periodic background scanner, ATS scoring, tailored application drafting, and full correspondence tracking.

---

## 🌟 Key Features

- **🧠 Alex — Conversational Career Wingman:**
  Talk naturally via text or **two-way voice (Speech-to-Text & Text-to-Speech)**. Alex coaches you through your job hunt, provides encouragement, and calls autonomous sub-agents on demand.

- **⏱️ Autonomous 10-Minute Background Scout:**
  Runs silently in the background every 10 minutes, querying major job platforms for new openings, scoring them against your profile, and broadcasting live notifications over WebSockets.

- **🎯 ATS Matcher Agent (0–100 Scoring):**
  Evaluates skill overlaps, tech stack compatibility (PyTorch, TensorFlow, Scikit-Learn, LSTMs, FastAPI), seniority, and location preferences with clear match rationales.

- **✍️ Writer Agent with Real Project Evidence:**
  Crafts tailored, non-generic 3-paragraph cover letters and cold outreach emails directly highlighting real GitHub projects (like **VehicleIQ** and **RecruitIQ**) and linking your verified LinkedIn & GitHub profiles.

- **📋 Kanban Applications Tracker:**
  Visual drag-and-drop workflow tracking applications across `Applied` ➔ `In Review` ➔ `Interview` ➔ `Offer` / `Rejected`.

- **📬 Emails & Reverts Mailbox:**
  Records all dispatched applications and company revert-back receipts ("Thanks for applying!") in real time.

---

## 🏗️ Multi-Agent Architecture

```
                       ┌─────────────────────────┐
                       │     User Interface      │
                       │ (Glassmorphic SPA / Web)│
                       └────────────┬────────────┘
                                    │ WebSockets / REST
                                    ▼
                       ┌─────────────────────────┐
                       │  Alex (Orchestrator)    │
                       └─┬──────────┬──────────┬─┘
                         │          │          │
         ┌───────────────┘          │          └───────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Scraper Manager │       │  Matcher Agent  │       │  Writer Agent   │
│ - LinkedIn      │       │ - ATS Scoring   │       │ - Cover Letters │
│ - Internshala   │       │ - Skill Gaps    │       │ - Cold Emails   │
│ - Naukri/Indeed │       │ - Profile Fit   │       │ - GitHub & Projs│
└─────────────────┘       └─────────────────┘       └─────────────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │  Tracker Agent & DB     │
                       │ (Async SQLite Storage)  │
                       └─────────────────────────┘
```

---

## 🚀 Quick Start (Local)

### 1. Clone the repository
```bash
git clone https://github.com/Jyotiraditya1006/JobAgent.git
cd JobAgent
```

### 2. Create virtual environment & install dependencies
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables (optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your `GEMINI_API_KEY` for live generative responses (runs with intelligent local fallback if not configured).

### 4. Run the server
```bash
python app.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser!

---

## ☁️ Deploying on Render (Free Web Service)

This repository is pre-configured with **`render.yaml`** and a production-grade **`Dockerfile`**.

### Method 1: Render Blueprint (Recommended)
1. Push this repository to your GitHub account (`https://github.com/Jyotiraditya1006/JobAgent`).
2. Go to your [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** ➔ **Blueprint**.
4. Connect your `JobAgent` repository. Render will automatically detect `render.yaml` and set up the Web Service.
5. Click **Apply**.

### Method 2: Manual Web Service
1. Click **New +** ➔ **Web Service**.
2. Connect your GitHub repository.
3. Configure the following settings:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Under **Environment Variables**, add:
   - `HOST` = `0.0.0.0`
   - `DEBUG` = `false`
   - `GEMINI_API_KEY` = *(your API key, optional)*
5. Click **Deploy Web Service**.

Your app will be live with a permanent public URL (e.g. `https://jobagent-ai.onrender.com`).

---

## 👨‍💻 Candidate Profile Pre-Configured

- **Name:** Jyotiraditya Patil
- **GitHub:** [github.com/Jyotiraditya1006](https://github.com/Jyotiraditya1006)
- **LinkedIn:** [linkedin.com/in/jyotiraditya-patil-73b394274](https://www.linkedin.com/in/jyotiraditya-patil-73b394274/)
- **Specialization:** B.Tech CSE (Artificial Intelligence & Machine Learning)
- **Flagship Projects:**
  - **VehicleIQ:** Real-Time OBD-II Telemetry Processing with TensorFlow LSTM & FastAPI
  - **RecruitIQ:** Full-Stack AI Candidate & Job Intelligence Platform
  - **LSTM Stock Predictor:** Deep Learning Temporal Sequence Forecasting
  - **Customer Churn System:** End-to-End ML Classification & Feature Importance

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
