# AI Knowledge Assistant

An AI-powered document intelligence platform that allows users to upload PDF documents and ask questions about their content using Retrieval-Augmented Generation (RAG).

The system combines **FastAPI, React, PostgreSQL, pgvector, LangChain, LangGraph, Gemini, Redis, JWT authentication, and Server-Sent Events (SSE)** to provide grounded AI answers with document sources.

## 🚀 Features

* 🔐 JWT-based user authentication
* 📄 PDF document upload
* ✂️ Automatic PDF text extraction and chunking
* 🧠 Document embeddings
* 🔎 Semantic vector search
* 🗄️ PostgreSQL + pgvector
* 🤖 Retrieval-Augmented Generation (RAG)
* 🦜 LangChain integration
* 🕸️ LangGraph-based RAG workflow
* ⚡ Server-Sent Events (SSE) streaming
* 💬 Conversation management
* 📚 Source-aware responses
* 📑 Document and page information for retrieved sources
* 📝 Markdown-formatted AI responses
* ⚡ Redis caching with graceful fallback
* 🎨 React + Tailwind CSS dashboard
* 🐳 Docker support

## 🏗️ System Architecture

```text
                         USER
                           │
                           ▼
                ┌─────────────────────┐
                │   React Frontend    │
                │  React + Tailwind   │
                └──────────┬──────────┘
                           │
                           │ SSE
                           ▼
                ┌─────────────────────┐
                │      FastAPI        │
                │   REST + JWT + SSE  │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │      LangGraph      │
                │    RAG Workflow     │
                └──────────┬──────────┘
                           │
                  ┌────────┴────────┐
                  │                 │
                  ▼                 ▼
        ┌──────────────────┐  ┌──────────────────┐
        │   Vector Search  │  │    LangChain     │
        │ PostgreSQL       │  │      Gemini      │
        │ + pgvector       │  │       LLM        │
        └────────┬─────────┘  └────────┬─────────┘
                 │                     │
                 └──────────┬──────────┘
                            ▼
                     Grounded Answer
                            │
                            ▼
                    Sources + Answer
                            │
                            ▼
                       React UI
```

## 🔄 RAG Pipeline

```text
PDF Upload
    ↓
PDF Text Extraction
    ↓
Text Cleaning
    ↓
Chunking
    ↓
Embedding Generation
    ↓
PostgreSQL + pgvector
    ↓
User Question
    ↓
Query Embedding
    ↓
Semantic Vector Search
    ↓
Relevant Document Chunks
    ↓
LangGraph RAG Workflow
    ↓
Gemini
    ↓
Grounded Answer
    ↓
Sources + Page Information
    ↓
React Frontend
```

## 🧠 How the RAG System Works

The assistant uses Retrieval-Augmented Generation instead of sending every question directly to the language model.

### 1. Document Upload

The user uploads a PDF through the React dashboard.

### 2. Text Extraction

The backend extracts text from the PDF using PDF processing tools.

### 3. Chunking

The extracted document is divided into smaller chunks so that relevant sections can be retrieved efficiently.

### 4. Embeddings

Each document chunk is converted into a numerical embedding representation.

### 5. Vector Storage

The embeddings and document metadata are stored in PostgreSQL using pgvector.

### 6. Semantic Search

When the user asks a question, the question is converted into an embedding and compared with stored document vectors.

### 7. Retrieval

The most relevant document chunks are retrieved from the vector database.

### 8. Generation

LangGraph manages the RAG workflow and LangChain connects the retrieved context with the Gemini language model.

### 9. Grounded Answer

Gemini generates an answer using the retrieved document information.

### 10. Sources

The application returns the answer together with relevant document and page information.

## 🛠️ Technology Stack

### Frontend

* React
* Vite
* Tailwind CSS
* React Markdown
* JavaScript

### Backend

* Python
* FastAPI
* SQLAlchemy
* JWT Authentication
* Server-Sent Events

### AI / GenAI

* Google Gemini
* LangChain
* LangGraph
* Retrieval-Augmented Generation
* Text Embeddings
* Semantic Search

### Database

* PostgreSQL
* pgvector

### Caching

* Redis

### DevOps

* Docker
* Git
* GitHub

## 📁 Project Structure

```text
AI-Knowledge-Assistant/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── config.py
│   ├── models.py
│   │
│   ├── routers/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   └── documents.py
│   │
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── embedding_service.py
│   │   ├── vector_search.py
│   │   ├── document_service.py
│   │   ├── rag_service.py
│   │   ├── langchain_service.py
│   │   ├── langchain_rag_service.py
│   │   ├── langgraph_rag_service.py
│   │   ├── redis_service.py
│   │   └── auth_service.py
│   │
│   └── schemas/
│       ├── auth.py
│       ├── chat.py
│       └── document.py
│
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       └── index.css
│
├── tests/
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

## ⚙️ Installation

### Clone the repository

```bash
git clone https://github.com/darmavaramharshavardan-bot/AI-Knowledge-Assistant.git
cd AI-Knowledge-Assistant
```

### Create Python virtual environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

### Install backend dependencies

```powershell
pip install -r requirements.txt
```

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=your_postgresql_connection_string
REDIS_URL=your_redis_connection_string
SECRET_KEY=your_secret_key
```

**Never commit `.env` to GitHub.**

The project already includes `.env` in `.gitignore`.

## ▶️ Run the Backend

From the project root:

```powershell
uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

## ▶️ Run the Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## 🐳 Docker

Build the backend image:

```bash
docker build -t ai-knowledge-assistant .
```

Run the container:

```bash
docker run -p 8000:8000 ai-knowledge-assistant
```

## 🔐 Security

The application includes:

* JWT authentication
* Protected API endpoints
* User-specific documents
* User-specific conversations
* Conversation ownership validation
* Environment-based secrets
* `.env` excluded from Git
* CORS configuration

## 💬 Example Questions

After uploading a technical PDF, users can ask:

```text
What is self-attention?
```

```text
What is the difference between self-attention and multi-head attention?
```

```text
Explain the advantages of the Transformer architecture.
```

The assistant retrieves relevant document sections and generates a grounded response with source information.

## 🎯 What This Project Demonstrates

This project demonstrates practical experience with:

* Generative AI
* Retrieval-Augmented Generation
* Vector databases
* Semantic search
* LLM integration
* LangChain
* LangGraph
* FastAPI
* PostgreSQL
* pgvector
* Redis
* JWT authentication
* SSE streaming
* React
* Tailwind CSS
* Docker
* Git and GitHub

## 📌 Resume Description

**AI Knowledge Assistant — RAG-based Document Intelligence Platform**

Built an end-to-end AI knowledge assistant using FastAPI, LangChain, LangGraph, PostgreSQL/pgvector, Gemini, Redis, and React. Implemented PDF ingestion, document chunking, semantic vector search, grounded RAG generation, JWT authentication, conversation management, SSE streaming, and source-aware responses through a responsive web dashboard.

## 🚀 Future Improvements

Possible future improvements include:

* Multi-document collections
* Conversation search
* Hybrid keyword + vector search
* Reranking
* Background document processing
* Advanced retrieval strategies
* Production deployment
* Monitoring and observability

## 👨‍💻 Author

**Harsha**

Computer Science and Engineering Student

Interested in:

* Artificial Intelligence
* Generative AI
* LLMs
* RAG
* AI Agents
* AI Engineering
