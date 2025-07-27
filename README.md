# AI-Powered RAG Chatbot with Vector Search

This project is an AI-powered chatbot with Retrieval-Augmented Generation (RAG) capabilities, featuring a Next.js frontend and Flask backend with vector search functionality.

## 🚀 Live Demo

- **Frontend**: Deployed on Render - [https://rag-chatbot-nextjs-1.onrender.com/](frontend)
- **Backend**: Self-hosted with Coolify on custom domain - [https://api.pmshaver.pro](backend)

*Note: Frontend may take 30-60 seconds to load initially due to Render's free tier cold starts.*

## 🏗️ Architecture

**Frontend (Next.js)**
- Deployed on Render (Free tier - Static deployment)
- TypeScript + Tailwind CSS + Radix UI
- Handles user interface and API communication

**Backend (Flask + AI)**
- Self-hosted using Coolify with Docker
- Custom domain deployment
- AI-powered chat with vector search
- Handles web crawling and embeddings


## 🔧 API Endpoints

The Flask backend provides these endpoints:

- `GET /health` - Health check and system status
- `GET /` - Root endpoint with API overview
- `POST /api/demo-mode` - Start demo mode with pre-loaded content
- `GET /api/demo-status` - Check demo mode loading status
- `POST /api/store-config` - Store API keys and URLs for custom crawling
- `POST /api/crawl-and-vectorize` - Crawl stored URLs and create vector embeddings
- `GET /api/vectorization-status` - Get real-time crawling/vectorization progress
- `POST /api/chat` - Chat with AI using vector search or general conversation
- `GET /api/status` - Get current backend status and configuration
- `GET /api/debug-status` - Detailed debug information


## 🚀 Deployment Information

### Backend Deployment (Coolify + Docker)

The backend is deployed using **Coolify** on a self-hosted server with Docker:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.backend_server:app"]
```

**Deployment Features:**
- Custom domain with SSL certificate
- Docker containerization
- Auto-deployment from Git
- Environment variable management
- Health checks and monitoring

### Frontend Deployment (Render Static)

The frontend is deployed on **Render's free tier** as a static Next.js application:

**Build Settings:**
- Build Command: `npm install && npm run build`
- Start Command: `npm start`
- Node Version: 18.x
- Auto-deploy from GitHub

**Performance Notes:**
- ⚠️ **Initial Load Time**: Frontend may take 30-60 seconds to load due to Render's free tier cold start
- Subsequent requests are faster once the service is warm
- Consider upgrading to paid tier for instant loading

## 🔧 Local Development

### 1. Backend Setup (Flask Server)

```bash
cd backend
pip install -r requirements.txt
python app/backend_server.py
```

The backend runs on `localhost:5000` and handles:
- API key management (Pinecone, Gemini AI, Firecrawl)
- URL crawling and content extraction
- Vector embeddings with sentence-transformers
- AI chat responses using Google Gemini

### 2. Frontend Setup (Next.js)

```bash
cd frontend/project
npm install
npm run dev
```

Frontend runs on `localhost:3000` with features:
- Modern chat interface
- Real-time status updates
- API key management
- URL configuration

## 📋 Environment Variables

### Backend (.env)
```env
GEMINI_API_KEY=your-gemini-api-key-here
PINECONE_API_KEY=your-pinecone-api-key-here
FIRECRAWL_API_KEY=your-firecrawl-api-key-here
PINECONE_INDEX_NAME=airport-index
```

### Frontend (.env)
```env
NEXT_PUBLIC_BACKEND_URL=https://api.yourdomain.com
```

## 🤖 AI Implementation

**Google Gemini Integration** (Changed from OpenAI for cost optimization)

- **Model**: Gemini 1.5 Flash
- **Reason for Switch**: Cost-effective alternative to OpenAI GPT-4
- **Features**: 
  - Retrieval-Augmented Generation (RAG)
  - Vector similarity search
  - Context-aware responses
  - Semantic search capabilities

**Vector Search Stack:**
- **Embeddings**: BAAI/bge-small-en-v1.5 (384 dimensions)
- **Vector DB**: Pinecone (serverless)
- **Search**: Semantic similarity with cosine distance
- **Content Processing**: Firecrawl for web scraping

## 🔄 Application Flow

```
Frontend (Next.js) → Backend (Flask) → External APIs
    ↓                    ↓               ↓
localhost:3000      localhost:5000   Firecrawl/OpenAI
```

1. Frontend sends API keys and URLs to backend
2. Backend stores configuration and crawls URLs
3. User asks questions in chat
4. Backend uses crawled content as context for OpenAI
5. AI responses are sent back to frontend

## 🛠️ Technical Stack

**Frontend:**
- Next.js 13.5.1
- TypeScript
- Tailwind CSS
- Radix UI components

**Backend:**
- Flask 3.0.0
- Python 3.8+
- OpenAI API
- Firecrawl API
- CORS enabled

## 🚨 Troubleshooting

### Backend Connection Issues
- Ensure Flask server is running on localhost:5000
- Check that CORS is enabled
- Verify API keys are loaded correctly

### API Key Issues
- Check environment variables are set correctly
- Verify API keys are valid and have sufficient credits
- Use manual entry if environment loading fails

### Crawling Issues
- Ensure URLs are accessible and valid
- Check Firecrawl API key and credits
- Verify network connectivity

## 📝 Example Usage

1. Start backend: `python app/start_backend.py`
2. Start frontend: `cd project && npm run dev`
3. Open browser: `http://localhost:3000`
4. Enter API keys or use environment variables
5. Add URLs like `https://example.com`
6. Click "Start Crawling & Chat"
7. Ask questions about the crawled content

## 🔐 Security Notes

- API keys are stored temporarily in backend memory
- Use environment variables for production
- CORS is enabled for localhost development
- Consider authentication for production use 