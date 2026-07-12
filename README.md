# 🚀 Portfolio AI Chatbot Backend — Groq API & RAG

A lightning-fast, production-ready AI Chatbot Backend designed to serve as a **personal portfolio assistant** for developers, designers, and creators. Powered by **FastAPI**, **Groq LLM API (`llama-3.1-8b-instant`)**, and a **Precision RAG (Retrieval-Augmented Generation)** pipeline.

The assistant answers recruiter and visitor questions **strictly based on your portfolio data** (`chunks.json`) — preventing AI hallucinations, fabricated links, or outside guesses.

---

## ✨ Features

- ⚡ **Lightning-Fast Responses:** Powered by Groq's LPU inference engine (`llama-3.1-8b-instant`).
- 🎯 **Strict RAG & Guardrails:** Answers *only* using retrieved chunks from your knowledge base. Politely declines off-topic or prompt injection attempts.
- 💬 **Multi-Turn Conversation Memory:** Remembers context across follow-up questions (`POST /chat` with `history`).
- 🛡️ **Built-In Security & Rate Limiting:** Sliding-window per-IP rate limiter (`15 req/min`) and configurable CORS middleware.
- 🔌 **100% Plug-and-Play:** Customize it for **your own portfolio** in under 5 minutes by replacing `chunks.json` and setting your Groq API key!

---

## 🛠️ Use This Chatbot With Your Own Data (3 Simple Steps)

You don't need any complex database setup. All you need is **one API key** and **one JSON file**:

### Step 1: Get a Free Groq API Key
1. Go to [GroqCloud Console](https://console.groq.com/).
2. Create an account and generate a free API key.

### Step 2: Create Your `.env` File
Copy `.env.example` to `.env` in the root directory:
```bash
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
ALLOWED_ORIGINS=*
RATE_LIMIT_PER_MIN=15
```

### Step 3: Replace `chunks.json` With Your Own Data
Edit `chunks.json` in the root directory. Each entry represents a section or project in your portfolio:

```json
[
  {
    "id": "1_profile",
    "type": "section",
    "title": "1. Profile",
    "content": "- **Name:** Jane Doe\n- **Title:** Full Stack Engineer\n- **Bio:** Software engineer specializing in React, Python, and AI systems.\n- **Location:** San Francisco, CA\n- **Email:** jane@example.com\n- **LinkedIn:** https://linkedin.com/in/janedoe\n- **Portfolio:** https://janedoe.dev"
  },
  {
    "id": "2_education",
    "type": "section",
    "title": "2. Education",
    "content": "- **Degree:** BS Computer Science, Stanford University (2024)"
  },
  {
    "id": "3_tech_stack",
    "type": "section",
    "title": "3. Tech Stack",
    "content": "- **Languages:** TypeScript, Python, C++\n- **Frameworks:** React, Next.js, FastAPI"
  },
  {
    "id": "project_ai_assistant",
    "type": "item",
    "title": "Smart AI Assistant (Featured Project)",
    "content": "- **Short description:** An intelligent developer assistant powered by RAG.\n- **Tech stack:** React, FastAPI, Groq API\n- **Details:** Built a full-stack chatbot platform that indexes docs and serves real-time answers.\n- **Links:** live: https://example.com | repo: https://github.com/janedoe/project"
  }
]
```

> **Tip:** Keep chunk titles descriptive (e.g., `"Project Name - Description"`) so the RAG relevance scorer ranks them accurately!

---

## 🏃 Setup & Running Locally

### 1. Install Python Dependencies
Make sure you have Python 3.10+ installed:
```bash
pip install -r requirements.txt
```

### 2. Start the FastAPI Dev Server
```bash
uvicorn main:app --reload --port 8000
```
The server will start at `http://localhost:8000`. You can visit Swagger interactive docs at `http://localhost:8000/docs`.

---

## 📡 API Endpoints & Usage

### 1. `POST /chat` — Multi-Turn Conversational Chat (Recommended)
Remembers previous messages so visitors can ask follow-up questions.

**Request Body:**
```json
{
  "message": "What tech stack did she use for Smart AI Assistant?",
  "history": [
    {
      "role": "user",
      "content": "Tell me about Smart AI Assistant"
    },
    {
      "role": "assistant",
      "content": "Smart AI Assistant is an intelligent developer assistant built by Jane Doe..."
    }
  ]
}
```

**Response Body:**
```json
{
  "reply": "For Smart AI Assistant, Jane used React on the frontend and FastAPI with Groq API on the backend."
}
```

---

### 2. `POST /ask` — Single-Turn Question
For quick, single-shot widgets without conversation history.

**Request Body:**
```json
{
  "question": "What is Jane's email address?"
}
```

**Response Body:**
```json
{
  "answer": "You can reach Jane at jane@example.com.",
  "reply": "You can reach Jane at jane@example.com."
}
```

---

### 3. `GET /health` — Health Check
Used by deployment platforms (Render, Vercel, AWS, Docker) to verify server status.

```json
{
  "status": "ok",
  "model": "llama-3.1-8b-instant"
}
```

---

## 💻 Frontend Integration Snippet (React / Vanilla JS)

Integrate the chatbot into your website with a simple `fetch` call:

```javascript
async function askPortfolioBot(userMessage, conversationHistory = []) {
  const res = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: userMessage,
      history: conversationHistory
    })
  });

  if (!res.ok) throw new Error("API request failed");
  const data = await res.json();
  return data.reply;
}
```

---

## 🐳 Docker Deployment

A clean `Dockerfile` is included. To build and run containerized:

```bash
docker build -t portfolio-chatbot .
docker run -p 8000:8000 --env-file .env portfolio-chatbot
```

---

## 📄 License
MIT License. Feel free to use, fork, and adapt for your own portfolio!
