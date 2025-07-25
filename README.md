# Chatbot with Backend Integration

This project integrates a Next.js chatbot frontend with a Flask backend server that handles API keys, URL crawling, and AI chat functionality.

## 🚀 Quick Start

### 1. Backend Setup (Flask Server on localhost:5000)

The backend server handles:
- API key management (PinecodeDB, OpenAI, Firecrawl)
- URL crawling using Firecrawl API
- AI chat responses using OpenAI API
- Environment variable loading

#### Option A: Automatic Setup
```bash
cd app
python start_backend.py
```

#### Option B: Manual Setup
```bash
cd app
pip install -r requirements.txt
python backend_server.py
```

### 2. Frontend Setup (Next.js on localhost:3000)

```bash
cd project
npm install
npm run dev
```

## 📋 Environment Variables

Create `app/.env` file with your API keys:

```env
OPENAI_API_KEY=sk-proj-your-openai-key-here
PINECONE_API_KEY=pcsk_your-pinecone-key-here
FIRECRAWL_API_KEY=fc-your-firecrawl-key-here
```

**Note**: The app will work without environment variables - you can enter API keys manually in the frontend.

## 🔧 API Endpoints

The Flask backend provides these endpoints:

- `GET /health` - Health check
- `POST /api/store-config` - Store API keys and URLs
- `POST /api/crawl-urls` - Crawl stored URLs using Firecrawl
- `POST /api/chat` - Chat with AI using crawled content
- `GET /api/status` - Get current backend status

## 🎯 How It Works

1. **Start Backend**: Run the Flask server on localhost:5000
2. **Start Frontend**: Run the Next.js app on localhost:3000
3. **Configure APIs**: Enter API keys (or use environment variables)
4. **Add URLs**: Add websites to crawl for content
5. **Crawl Content**: Backend uses Firecrawl API to extract content
6. **Chat**: Ask questions and get AI responses based on crawled content

## 🔄 Data Flow

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