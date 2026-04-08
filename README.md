#  🚨 CrisisOps AI
Autonomous Multi-Agent Incident Response System

CrisisOps AI is an intelligent, autonomous incident response platform designed to handle critical system failures in real time. It leverages Google’s Gemini models and a multi-agent orchestration framework to triage incidents, notify stakeholders, and generate post-mortems without manual intervention.

---

##  📽️ Live Demo
- Dashboard: https://crisis-ops-ai-253590687342.us-central1.run.app
- Deployed on: Google Cloud Run

---

##  🛠️ What It Does
CrisisOps AI replaces manual incident handling with an AI-driven multi-agent workflow:

1. Incident Intake – Parses raw alerts/logs
2. Triage and Root Cause Analysis – Identifies severity and likely causes
3. Stakeholder Communication – Sends automated updates via Slack, Creates War Rooms etc.,.
4. Post-Mortem Generation – Produces structured incident reports

---

## 🤖  Multi-Agent Architecture

Leader–Follower Design (Google ADK)

- Commander Agent (Leader)  
  Orchestrates the workflow and coordinates agents

- Triage Agent  
  Performs root cause analysis and suggests fixes

- Communication Agent  
  Sends real-time alerts via Slack, Creates War Rooms etc.,.

- Documentation Agent  
  Generates post-mortems and action items

---

## ✨ Key Features

- Fully autonomous incident response pipeline
- Powered by Gemini models
- Real-time monitoring dashboard (React)
- Slack integration for alerts
- Structured incident logging (PostgreSQL)
- Vector search for historical incidents (planned)

---

## Tech Stack

Backend:
- Python, Flask, SQLAlchemy
- PostgreSQL (Cloud SQL)
- Gunicorn / Uvicorn

Frontend:
- React, Vite, Axios

AI and Orchestration:
- Google Gemini
- Google ADK

Infrastructure:
- Google Cloud Run
- Artifact Registry
- Secret Manager

---

## Getting Started

Prerequisites:
- Python 3.11+
- Node.js 20+
- Google Cloud project with Gemini API access

---

## Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/KongaraLikhith/crisis-ops-ai.git
cd crisis-ops-ai
```
### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```
### 3. Frontend
```bash
cd ../frontend
npm install
npm run dev
```
## Deployment (Cloud Run)
The project is optimized for **Google Cloud Run**. To deploy your own instance:
```bash
gcloud run deploy crisis-ops-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```
---

## 🔮Future Enhancements

- Role-based access control
- Incident analytics dashboard (MTTR, trends)
- Memory layer for learning across incidents

---

## 🤝Contributors
Built with ❤️ during the **Google GenAI Hackathon**. 

- [Mohith Raghav](https://github.com/MyThunder-World)
- [Mayank Porwal](https://github.com/mayank-porwal-da)
- [Vijay](https://github.com/vijay-sb)
- [Likhith K](https://github.com/KongaraLikhith)

---

