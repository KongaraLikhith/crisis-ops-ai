# 🚀 CrisisOps AI
**Autonomous Multi-Agent Incident Response & Documentation System**

CrisisOps AI is a cutting-edge, autonomous emergency response platform designed to streamline incident management during critical system failures. Leveraging Google's **Gemini 1.5/2.5** models and the **Google ADK (Agent Development Kit)**, CrisisOps AI orchestrates a team of specialized agents to handle triage, stakeholder communication, and post-mortem documentation in real-time.

---

## 📽️ Demo & Deployment
- **Live Dashboard**: [https://crisis-ops-ai-253590687342.us-central1.run.app](https://crisis-ops-ai-253590687342.us-central1.run.app)
- **Deployment Platform**: Google Cloud Run (Unified Container)

---

## ✨ Key Features
- **🤖 Autonomous Multi-Agent Pipeline**: 
  - **Intake Agent**: Parses raw incident reports and initializes response.
  - **Triage Agent**: Analyzes root causes and suggests technical resolutions.
  - **Communication Agent**: Automated stakeholder alerts via **Slack**.
  - **Documentation Agent**: Generates comprehensive post-mortems and next-steps.
- **⚡ Real-time Hybrid Dashboard**: A sleek React-based interface to monitor agent activity and incident status.
- **🛠️ MCP Integration**: Ready for Google Workspace (Gmail, Docs, Calendar) via Managed Model Context Protocol.
- **🧠 Intelligent Vector Search**: (Upcoming) Contextual awareness of past incidents to speed up resolution.

---

## 🏗️ Technical Architecture
CrisisOps AI uses a **Leader-Follower** architecture powered by the Google ADK:
- **Leader**: `CommanderAgent` orchestrates the workflow.
- **Followers**: Specialized sub-agents for Triage, Comms, and Docs.
- **Backend**: Flask + SQLAlchemy (PostgreSQL) + Uvicorn/Gunicorn.
- **Frontend**: React + Vite + Vanilla CSS (Glassmorphism design).

---

## 🛠️ Built With
- **LLM**: Google Gemini 1.5 Flash / 2.5 Flash
- **Framework**: [Google ADK](https://github.com/google/adk)
- **Backend**: Python, Flask, Psycopg3
- **Frontend**: React, Vite, Axios
- **Database**: Google Cloud SQL (PostgreSQL)
- **Infrastructure**: Google Cloud Run, Artifact Registry, Secret Manager

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Google Cloud Project with Gemini API access

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/KongaraLikhith/crisis-ops-ai.git
   cd crisis-ops-ai
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env # Add your API keys here
   python main.py
   ```

3. **Frontend Setup**:
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

### ☁️ Cloud Deployment
The project is optimized for **Google Cloud Run**. To deploy your own instance:
```bash
gcloud run deploy crisis-ops-ai --source . --region us-central1 --allow-unauthenticated
```

---

## 🤝 Contributing
Built with ❤️ during the **Google AI Agent Hackathon**. 

- **Developers**: [Likhith Kongara](https://github.com/KongaraLikhith), [Mayank](https://github.com/mayank-sb)
- **Agentic Companion**: Antigravity (Powered by Google Deepmind)

---
*Empowering SREs with the power of Autonomy.*
