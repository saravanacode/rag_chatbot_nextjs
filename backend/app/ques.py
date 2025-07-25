from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import openai
import os
import dotenv

dotenv.load_dotenv()

# === CONFIG ===
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
INDEX_NAME = 'changiairport-index'
MODEL_NAME = 'BAAI/bge-small-en-v1.5'

# === INIT ===
print("🔄 Loading components...")
model = SentenceTransformer(MODEL_NAME)
pinecone = Pinecone(api_key=PINECONE_API_KEY)
index = pinecone.Index(INDEX_NAME)
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
print("✅ All components loaded!")

def search_and_answer(question, top_k=5):
    """
    Search the database and generate an AI answer
    
    Args:
        question (str): User's question
        top_k (int): Number of search results to consider
    
    Returns:
        dict: Contains the AI answer and sources
    """
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
            'answer': "I couldn't find any relevant information about that topic.",
            'sources': [],
            'confidence': 0
        }
    
    # 2. Collect relevant context
    context_pieces = []
    sources = []
    
    for match in results['matches']:
        if match['score'] > 0.5:  # Only reasonably relevant results
            content = match['metadata'].get('full_content', '')
            url = match['metadata'].get('url', 'Unknown')
            
            if content and len(content) > 50:  # Skip very short content
                context_pieces.append(content)
                sources.append(url)
    
    if not context_pieces:
        return {
            'answer': "I found some results but they don't seem directly relevant to your question.",
            'sources': [],
            'confidence': 0
        }
    
    # 3. Combine context (limit to avoid token limits)
    combined_context = '\n\n---\n\n'.join(context_pieces[:3])  # Top 3 results
    if len(combined_context) > 4000:  # Limit context size
        combined_context = combined_context[:4000] + "..."
    
    # 4. Generate AI answer using OpenAI
    print("🤖 Generating AI answer...")
    
    system_prompt = """You are a helpful assistant for Changi Airport in Singapore. 
    Use the provided context to answer questions about the airport.
    
    Guidelines:
    - Be helpful, accurate, and concise
    - Only use information from the provided context
    - If the context doesn't contain enough information, say so
    - Include specific details like locations, timings, or procedures when available
    - Be friendly and professional
    """
    
    user_prompt = f"""Question: {question}

Context from Changi Airport website:
{combined_context}

Please provide a helpful answer based on the context above."""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-3.5-turbo" for cheaper option
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.3  # Lower temperature for more factual responses
        )
        
        ai_answer = response.choices[0].message.content
        
        return {
            'answer': ai_answer,
            'sources': list(set(sources)),  # Remove duplicates
            'confidence': results['matches'][0]['score'],
            'raw_results': len(results['matches'])
        }
        
    except Exception as e:
        return {
            'answer': f"Sorry, I encountered an error generating the answer: {str(e)}",
            'sources': sources,
            'confidence': 0
        }

def print_ai_response(response):
    """Pretty print the AI response"""
    print("\n" + "="*80)
    print("🤖 AI ASSISTANT RESPONSE")
    print("="*80)
    
    print(f"\n📝 Answer:")
    print(response['answer'])
    
    if response['sources']:
        print(f"\n🔗 Sources ({len(response['sources'])} found):")
        for i, source in enumerate(response['sources'][:5], 1):
            print(f"   {i}. {source}")
    
    print(f"\n📊 Confidence: {response['confidence']:.1%}")
    print(f"📈 Results processed: {response.get('raw_results', 0)}")
    print("="*80)

def interactive_ai_assistant():
    """Interactive AI assistant for Changi Airport"""
    print("\n🛫 CHANGI AIRPORT AI ASSISTANT")
    print("Ask me anything about Changi Airport and I'll provide detailed answers!")
    print("Type 'quit' to exit, 'help' for example questions")
    print("="*80)
    
    example_questions = [
        "Where can I find restaurants in Terminal 3?",
        "How do I connect to free WiFi at Changi?",
        "What shopping options are available?",
        "How do I get from the airport to Marina Bay Sands?",
        "Where are the prayer rooms located?",
        "What lounges can I access with Priority Pass?",
        "How early should I arrive for international flights?",
        "Where can I store my luggage?"
    ]
    
    while True:
        user_input = input("\n❓ Your question: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("👋 Thank you for using Changi Airport Assistant!")
            break
        
        if user_input.lower() == 'help':
            print("\n💡 Example questions you can ask:")
            for i, q in enumerate(example_questions, 1):
                print(f"   {i}. {q}")
            continue
        
        if not user_input:
            print("⚠️ Please enter a question or type 'help' for examples.")
            continue
        
        try:
            print("🔄 Processing your question...")
            response = search_and_answer(user_input)
            print_ai_response(response)
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")

# === BATCH TESTING ===
def test_ai_assistant():
    """Test the AI assistant with sample questions"""
    test_questions = [
        "Where can I eat at Changi Airport?",
        "How do I get free WiFi?",
        "What are the shopping options?",
        "How do I get to the city center?",
        "Where are the children's play areas?"
    ]
    
    print("🧪 TESTING AI ASSISTANT")
    print("="*80)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n🔍 Test {i}: {question}")
        response = search_and_answer(question)
        print_ai_response(response)
        
        if i < len(test_questions):
            input("\nPress Enter to continue to next test...")

if __name__ == "__main__":
    # Choose what to run
    mode = input("Choose mode:\n1. Interactive Assistant\n2. Run Tests\nEnter choice (1 or 2): ").strip()
    
    if mode == "2":
        test_ai_assistant()
    else:
        interactive_ai_assistant()