from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import json
from datetime import datetime
import dotenv
import asyncio
import threading
import time

# AI Assistant imports
try:
    print("🔄 Importing sentence-transformers...")
    from sentence_transformers import SentenceTransformer
    print("✅ sentence-transformers imported")
    
    print("🔄 Importing pinecone...")
    from pinecone import Pinecone, ServerlessSpec
    print("✅ pinecone imported")
    
    print("🔄 Importing google-generativeai...")
    import google.generativeai as genai
    print("✅ google-generativeai imported")
    
    print("🔄 Importing firecrawl...")
    from firecrawl import AsyncFirecrawlApp, ScrapeOptions
    print("✅ firecrawl imported")
    
    AI_IMPORTS_AVAILABLE = True
    print("🎉 All AI imports successful!")
except ImportError as e:
    print(f"❌ AI import failed: {e}")
    print(f"❌ Failed module: {e.name if hasattr(e, 'name') else 'unknown'}")
    AI_IMPORTS_AVAILABLE = False

# Load environment variables
dotenv.load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    "https://rag-chatbot-nextjs-1.onrender.com",
    "https://hipster-frontend.onrender.com", 
    "http://localhost:3000",
    "http://localhost:3001"
])  # Enable CORS for all routes

# Configuration from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY") 
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "airport-index")
MODEL_NAME = 'BAAI/bge-small-en-v1.5'

# Get port from environment (Render sets this)
PORT = int(os.environ.get('PORT', 5000))

print("🚀 Backend Server Starting...")
print(f"📡 Gemini API Key: {'✓ Loaded' if GEMINI_API_KEY else '✗ Missing'}")
print(f"📡 Pinecone API Key: {'✓ Loaded' if PINECONE_API_KEY else '✗ Missing'}")
print(f"📡 Firecrawl API Key: {'✓ Loaded' if FIRECRAWL_API_KEY else '✗ Missing'}")
print(f"🤖 AI Imports: {'✓ Available' if AI_IMPORTS_AVAILABLE else '✗ Missing'}")

# AI Assistant components (loaded lazily)
ai_components = {
    "model": None,
    "pinecone": None,
    "index": None,
    "gemini_model": None,
    "loaded": False
}

# Store API keys and URLs received from frontend
stored_data = {
    "api_keys": {},
    "urls": [],
    "crawled_data": [],
    "demo_mode": False,
    "vectorization_status": {
        "in_progress": False,
        "completed": False,
        "total_urls": 0,
        "processed_urls": 0,
        "successful_docs": 0,
        "errors": []
    }
}

def load_ai_components():
    """Load AI components for demo mode"""
    global ai_components
    
    if not AI_IMPORTS_AVAILABLE:
        raise Exception("AI libraries not installed. Please install: pip install sentence-transformers pinecone-client google-generativeai firecrawl-py")
    
    if ai_components["loaded"]:
        return ai_components
    
    print("🔄 Loading AI components...")
    
    try:
        # Load sentence transformer model
        ai_components["model"] = SentenceTransformer(MODEL_NAME)
        print("✅ Sentence transformer model loaded")
        
        # Initialize Pinecone
        ai_components["pinecone"] = Pinecone(api_key=PINECONE_API_KEY)
        
        # Create index if not exists
        existing_indexes = [index.name for index in ai_components["pinecone"].list_indexes()]
        if INDEX_NAME not in existing_indexes:
            print(f"🔄 Creating Pinecone index: {INDEX_NAME}")
            ai_components["pinecone"].create_index(
                name=INDEX_NAME,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            print("⏳ Waiting for index to be ready...")
            time.sleep(10)
            print("✅ Index created!")
        else:
            print(f"✅ Index {INDEX_NAME} already exists!")
        
        ai_components["index"] = ai_components["pinecone"].Index(INDEX_NAME)
        print("✅ Pinecone connection established")
        
        # Initialize Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        ai_components["gemini_model"] = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini client initialized")
        
        ai_components["loaded"] = True
        print("🎉 All AI components loaded successfully!")
        
        return ai_components
        
    except Exception as e:
        print(f"❌ Error loading AI components: {str(e)}")
        raise e

async def process_urls_to_pinecone(url_list: list[str], firecrawl_key: str):
    """
    Process URLs to Pinecone vector database - adapted from new2.py
    """
    try:
        components = load_ai_components()
        model = components["model"]
        index = components["index"]
        
        app = AsyncFirecrawlApp(api_key=firecrawl_key)
        successful_uploads = 0
        
        stored_data["vectorization_status"]["in_progress"] = True
        stored_data["vectorization_status"]["total_urls"] = len(url_list)
        stored_data["vectorization_status"]["processed_urls"] = 0
        stored_data["vectorization_status"]["successful_docs"] = 0
        stored_data["vectorization_status"]["errors"] = []

        for i, base_url in enumerate(url_list):
            print(f"\n🕷️ Crawling: {base_url}")
            try:
                result = await app.crawl_url(
                    url=base_url,
                    limit=5,
                    max_depth=5,
                    allow_backward_links=True,
                    scrape_options=ScrapeOptions(
                        formats=["markdown"],
                        only_main_content=True,
                        parse_pdf=True,
                        max_age=14400000
                    )
                )

                # Parse documents
                if hasattr(result, 'data') and result.data:
                    documents = result.data
                elif isinstance(result, dict):
                    documents = result.get("data", result.get("documents", []))
                else:
                    documents = []

                print(f"✅ Scraped {len(documents)} documents from {base_url}")

                for doc_i, doc in enumerate(documents):
                    try:
                        if hasattr(doc, 'metadata'):
                            url = doc.metadata.get('sourceURL', f'doc_{doc_i}')
                            content = getattr(doc, 'markdown', '') or getattr(doc, 'content', '')
                        elif isinstance(doc, dict):
                            url = doc.get("metadata", {}).get("sourceURL") or doc.get("url", f"doc_{doc_i}")
                            content = doc.get("markdown", "") or doc.get("content", "")
                        else:
                            url = f"doc_{doc_i}"
                            content = str(doc)

                        content = content.strip()
                        if not content or len(content) < 50:
                            print(f"⚠️ Skipping short content from: {url}")
                            continue

                        print(f"🧠 Generating embedding for: {url}")
                        embedding = model.encode(content, normalize_embeddings=True).tolist()

                        doc_id = f"doc_{hash(url) % 100000}_{doc_i}"

                        index.upsert([{
                            "id": doc_id,
                            "values": embedding,
                            "metadata": {
                                "url": url,
                                "content": content[:500],
                                "full_content": content
                            }
                        }])

                        successful_uploads += 1
                        stored_data["vectorization_status"]["successful_docs"] = successful_uploads
                        print(f"✅ [{successful_uploads}] Indexed: {url}")

                    except Exception as e:
                        error_msg = f"Error processing document {doc_i} from {base_url}: {str(e)}"
                        print(f"❌ {error_msg}")
                        stored_data["vectorization_status"]["errors"].append(error_msg)
                        continue

                stored_data["vectorization_status"]["processed_urls"] = i + 1

            except Exception as e:
                error_msg = f"Error crawling {base_url}: {str(e)}"
                print(f"❌ {error_msg}")
                stored_data["vectorization_status"]["errors"].append(error_msg)
                stored_data["vectorization_status"]["processed_urls"] = i + 1
                continue

        stored_data["vectorization_status"]["in_progress"] = False
        stored_data["vectorization_status"]["completed"] = True
        
        print(f"\n🎉 Finished! Total successful documents indexed: {successful_uploads}")
        return successful_uploads
        
    except Exception as e:
        stored_data["vectorization_status"]["in_progress"] = False
        stored_data["vectorization_status"]["errors"].append(f"Fatal error: {str(e)}")
        print(f"❌ Fatal error in vectorization: {str(e)}")
        raise e

def run_vectorization_in_thread(url_list: list[str], firecrawl_key: str):
    """Run vectorization in a separate thread"""
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_urls_to_pinecone(url_list, firecrawl_key))
        except Exception as e:
            print(f"❌ Thread error: {str(e)}")
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_async)
    thread.daemon = True
    thread.start()

def search_and_answer(question, top_k=5):
    """
    Search the vector database and generate an AI answer using Gemini
    """
    try:
        components = load_ai_components()
        model = components["model"]
        index = components["index"]
        gemini_model = components["gemini_model"]
        
        print(f"🔍 Searching for: '{question}'")
        
        # 1. Search the vector database
        query_embedding = model.encode(question, normalize_embeddings=True).tolist()
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        if not results['matches']:
            return {
                'answer': "I couldn't find any relevant information about that topic in the vector database.",
                'sources': [],
                'confidence': 0,
                'method': 'vector_search'
            }
        
        # 2. Collect relevant context
        context_pieces = []
        sources = []
        
        for match in results['matches']:
            if match['score'] > 0.5:  # Only reasonably relevant results
                content = match['metadata'].get('full_content', '')
                url = match['metadata'].get('url', 'Vector Database')
                
                if content and len(content) > 50:  # Skip very short content
                    context_pieces.append(content)
                    sources.append(url)
        
        if not context_pieces:
            return {
                'answer': "I found some results but they don't seem directly relevant to your question.",
                'sources': [],
                'confidence': 0,
                'method': 'vector_search'
            }
        
        # 3. Combine context (limit to avoid token limits)
        combined_context = '\n\n---\n\n'.join(context_pieces[:3])  # Top 3 results
        if len(combined_context) > 4000:  # Limit context size
            combined_context = combined_context[:4000] + "..."
        
        # 4. Generate AI answer using Gemini
        print("🤖 Generating AI answer with Gemini...")
        
        prompt = f"""You are a helpful AI assistant with access to a vector database. 
Use the provided context to answer questions accurately.

Guidelines:
- Be helpful, accurate, and concise
- Only use information from the provided context
- If the context doesn't contain enough information, say so
- Include specific details when available
- Be friendly and professional

Question: {question}

Context from vector database:
{combined_context}

Please provide a helpful answer based on the context above."""
        
        response = gemini_model.generate_content(prompt)
        ai_answer = response.text
        
        return {
            'answer': ai_answer,
            'sources': list(set(sources)),  # Remove duplicates
            'confidence': results['matches'][0]['score'],
            'raw_results': len(results['matches']),
            'method': 'vector_search'
        }
        
    except Exception as e:
        return {
            'answer': f"Sorry, I encountered an error with the vector search: {str(e)}",
            'sources': [],
            'confidence': 0,
            'method': 'vector_search',
            'error': str(e)
        }

# Routes
@app.route('/', methods=['GET'])
def root():
    """Root endpoint for health checks"""
    return jsonify({
        "message": "Hipster Backend API is running!",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            "GET /health - Health check",
            "POST /api/demo-mode - Start demo mode",
            "POST /api/store-config - Store configuration",
            "POST /api/crawl-and-vectorize - Crawl and vectorize",
            "GET /api/vectorization-status - Get status",
            "POST /api/chat - Chat with AI",
            "GET /api/status - Get current status"
        ]
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "env_keys_loaded": {
            "gemini": bool(GEMINI_API_KEY),
            "pinecone": bool(PINECONE_API_KEY),
            "firecrawl": bool(FIRECRAWL_API_KEY)
        },
        "ai_imports_available": AI_IMPORTS_AVAILABLE,
        "ai_components_loaded": ai_components["loaded"]
    })

@app.route('/api/demo-status', methods=['GET'])
def get_demo_status():
    """Get demo mode loading status"""
    return jsonify({
        "success": True,
        "data": {
            "ai_components_loaded": ai_components["loaded"],
            "model_loaded": bool(ai_components.get("model")),
            "pinecone_connected": bool(ai_components.get("index")),
            "gemini_ready": bool(ai_components.get("gemini_model")),
            "demo_mode": stored_data.get('demo_mode', False)
        }
    })

@app.route('/api/demo-mode', methods=['POST'])
def start_demo_mode():
    """Start demo mode - load AI components and set demo flag"""
    try:
        if not AI_IMPORTS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "AI libraries not installed. Please install: pip install sentence-transformers pinecone-client google-generativeai firecrawl-py"
            }), 400
        
        if not GEMINI_API_KEY or not PINECONE_API_KEY:
            return jsonify({
                "success": False,
                "error": "Gemini and Pinecone API keys required for demo mode"
            }), 400
        
        # Start loading in background if not already loaded
        if not ai_components["loaded"]:
            def load_components():
                try:
                    load_ai_components()
                    stored_data['demo_mode'] = True
                    stored_data['api_keys'] = {
                        'pinecone': PINECONE_API_KEY,
                        'gemini': GEMINI_API_KEY
                    }
                    print("🎉 Demo mode fully loaded!")
                except Exception as e:
                    print(f"❌ Background loading failed: {e}")
            
            import threading
            thread = threading.Thread(target=load_components)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "success": True,
                "message": "Demo mode initialization started. Loading AI components...",
                "loading": True
            })
        else:
            # Already loaded
            stored_data['demo_mode'] = True
            stored_data['api_keys'] = {
                'pinecone': PINECONE_API_KEY,
                'gemini': GEMINI_API_KEY
            }
            return jsonify({
                "success": True,
                "message": "Demo mode started successfully! AI assistant is ready.",
                "loading": False,
                "data": {
                    "model_loaded": bool(ai_components["model"]),
                    "pinecone_connected": bool(ai_components["index"]),
                    "gemini_ready": bool(ai_components["gemini_model"]),
                    "index_name": INDEX_NAME,
                    "model_name": MODEL_NAME
                }
            })
        
    except Exception as e:
        print(f"❌ Error starting demo mode: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/crawl-and-vectorize', methods=['POST'])
def crawl_and_vectorize():
    """Crawl URLs and vectorize them using the new2.py approach"""
    try:
        if not stored_data['urls']:
            return jsonify({
                "success": False,
                "error": "No URLs to crawl. Please add URLs first."
            }), 400
            
        if not AI_IMPORTS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "AI libraries not installed. Please install: pip install sentence-transformers pinecone-client google-generativeai firecrawl-py"
            }), 400
            
        firecrawl_key = stored_data['api_keys'].get('firecrawl')
        if not firecrawl_key:
            return jsonify({
                "success": False,
                "error": "Firecrawl API key not available"
            }), 400
        
        if stored_data["vectorization_status"]["in_progress"]:
            return jsonify({
                "success": False,
                "error": "Vectorization already in progress"
            }), 400
        
        # Reset vectorization status
        stored_data["vectorization_status"] = {
            "in_progress": True,
            "completed": False,
            "total_urls": len(stored_data['urls']),
            "processed_urls": 0,
            "successful_docs": 0,
            "errors": []
        }
        
        # Start vectorization in background thread
        run_vectorization_in_thread(stored_data['urls'], firecrawl_key)
        
        return jsonify({
            "success": True,
            "message": "Crawling and vectorization started in background",
            "data": {
                "total_urls": len(stored_data['urls']),
                "urls": stored_data['urls'],
                "index_name": INDEX_NAME
            }
        })
        
    except Exception as e:
        print(f"❌ Error starting crawl and vectorize: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/vectorization-status', methods=['GET'])
def get_vectorization_status():
    """Get the current status of vectorization process"""
    return jsonify({
        "success": True,
        "data": stored_data["vectorization_status"]
    })

@app.route('/api/store-config', methods=['POST'])
def store_config():
    """Store API keys and URLs from frontend"""
    try:
        data = request.get_json()
        
        # Store API keys (use env vars as fallback)
        api_keys = data.get('apiKeys', {})
        stored_data['api_keys'] = {
            'pinecone': api_keys.get('pinecone') or PINECONE_API_KEY,
            'firecrawl': api_keys.get('firecrawl') or FIRECRAWL_API_KEY, 
            'gemini': api_keys.get('gemini') or GEMINI_API_KEY
        }
        
        # Store URLs
        urls = data.get('urls', [])
        stored_data['urls'] = urls
        
        # Reset demo mode and vectorization status if URLs are provided
        if urls:
            stored_data['demo_mode'] = False
            stored_data["vectorization_status"] = {
                "in_progress": False,
                "completed": False,
                "total_urls": 0,
                "processed_urls": 0,
                "successful_docs": 0,
                "errors": []
            }
        
        print(f"📝 Stored config: {len(urls)} URLs, API keys: {list(stored_data['api_keys'].keys())}")
        
        return jsonify({
            "success": True,
            "message": "Configuration stored successfully",
            "data": {
                "urls_count": len(urls),
                "api_keys_received": list(api_keys.keys()),
                "env_keys_used": {
                    "gemini": bool(GEMINI_API_KEY and not api_keys.get('gemini')),
                    "pinecone": bool(PINECONE_API_KEY and not api_keys.get('pinecone')),
                    "firecrawl": bool(FIRECRAWL_API_KEY and not api_keys.get('firecrawl'))
                }
            }
        })
        
    except Exception as e:
        print(f"❌ Error storing config: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests using Gemini API"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({
                "success": False,
                "error": "No message provided"
            }), 400
        
        gemini_key = stored_data['api_keys'].get('gemini')
        if not gemini_key:
            return jsonify({
                "success": False,
                "error": "Gemini API key not available"
            }), 400
        
        # Check if we should use vector search (demo mode OR completed vectorization)
        use_vector_search = (stored_data.get('demo_mode') or 
                           stored_data["vectorization_status"].get("completed", False)) and AI_IMPORTS_AVAILABLE
        
        if use_vector_search:
            try:
                result = search_and_answer(user_message)
                return jsonify({
                    "success": True,
                    "response": result['answer'],
                    "method": result['method'],
                    "sources": result.get('sources', []),
                    "confidence": result.get('confidence', 0),
                    "demo_mode": stored_data.get('demo_mode', False),
                    "vectorized": stored_data["vectorization_status"].get("completed", False)
                })
            except Exception as vector_error:
                print(f"⚠️ Vector search failed, falling back to regular mode: {vector_error}")
        
        # Fallback to regular Gemini chat without context
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""You are a helpful AI assistant. Answer questions to the best of your ability.

User question: {user_message}"""
            
            response = model.generate_content(prompt)
            ai_response = response.text
            
            return jsonify({
                "success": True,
                "response": ai_response,
                "method": "general_chat",
                "demo_mode": False,
                "vectorized": False
            })
            
        except Exception as gemini_error:
            return jsonify({
                "success": False,
                "error": f"Gemini API error: {str(gemini_error)}"
            }), 500
            
    except Exception as e:
        print(f"❌ Error in chat: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current status of stored data"""
    return jsonify({
        "api_keys_configured": len(stored_data['api_keys']),
        "urls_stored": len(stored_data['urls']),
        "crawled_data_available": len(stored_data['crawled_data']),
        "successful_crawls": len([r for r in stored_data['crawled_data'] if r.get('success')]),
        "urls": stored_data['urls'],
        "demo_mode": stored_data.get('demo_mode', False),
        "ai_components_loaded": ai_components["loaded"],
        "vectorization_status": stored_data["vectorization_status"],
        "env_keys": {
            "gemini": bool(GEMINI_API_KEY),
            "pinecone": bool(PINECONE_API_KEY), 
            "firecrawl": bool(FIRECRAWL_API_KEY)
        }
    })

@app.route('/api/debug-status', methods=['GET'])
def debug_status():
    """Debug endpoint to see exact vectorization status"""
    return jsonify({
        "vectorization_status": stored_data["vectorization_status"],
        "demo_mode": stored_data.get('demo_mode', False),
        "ai_components_loaded": ai_components["loaded"],
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🌟 Starting Flask Backend Server")
    print(f"📡 Port: {PORT}")
    print("📡 API Endpoints:")
    print("   GET  /health - Health check")
    print("   POST /api/demo-mode - Start demo mode with AI assistant")
    print("   POST /api/store-config - Store API keys and URLs")
    print("   POST /api/crawl-and-vectorize - Crawl and vectorize URLs")
    print("   GET  /api/vectorization-status - Get vectorization progress")
    print("   POST /api/chat - Chat with AI using vector search or general chat")
    print("   GET  /api/status - Get current status")
    print("="*50)
    
    # Bind to 0.0.0.0 for Render
    app.run(host='0.0.0.0', port=PORT, debug=False)