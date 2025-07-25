import asyncio
from firecrawl import AsyncFirecrawlApp, ScrapeOptions
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import os
import dotenv
import time

dotenv.load_dotenv()

# === CONFIG ===
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = 'airport-index'
MODEL_NAME = 'BAAI/bge-small-en-v1.5'  # Can be swapped with any supported transformer model

# === INIT ===
print("🔄 Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)
print("✅ Model loaded!")

print("🔄 Setting up Pinecone...")
pinecone = Pinecone(api_key=PINECONE_API_KEY)

# Create index if not exists
existing_indexes = [index.name for index in pinecone.list_indexes()]
if INDEX_NAME not in existing_indexes:
    print(f"🔄 Creating Pinecone index: {INDEX_NAME}")
    pinecone.create_index(
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

index = pinecone.Index(INDEX_NAME)

# === MAIN EMBEDDING FUNCTION ===
async def process_urls_to_pinecone(url_list: list[str]):
    app = AsyncFirecrawlApp(api_key=FIRECRAWL_API_KEY)
    successful_uploads = 0

    for base_url in url_list:
        print(f"\n🕷️ Crawling: {base_url}")
        try:
            result = await app.crawl_url(
                url=base_url,
                limit=70,
                max_depth=70,
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

            for i, doc in enumerate(documents):
                try:
                    if hasattr(doc, 'metadata'):
                        url = doc.metadata.get('sourceURL', f'doc_{i}')
                        content = getattr(doc, 'markdown', '') or getattr(doc, 'content', '')
                    elif isinstance(doc, dict):
                        url = doc.get("metadata", {}).get("sourceURL") or doc.get("url", f"doc_{i}")
                        content = doc.get("markdown", "") or doc.get("content", "")
                    else:
                        url = f"doc_{i}"
                        content = str(doc)

                    content = content.strip()
                    if not content or len(content) < 50:
                        print(f"⚠️ Skipping short content from: {url}")
                        continue

                    print(f"🧠 Generating embedding for: {url}")
                    embedding = model.encode(content, normalize_embeddings=True).tolist()

                    doc_id = f"doc_{hash(url) % 100000}_{i}"

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
                    print(f"✅ [{successful_uploads}] Indexed: {url}")

                except Exception as e:
                    print(f"❌ Error processing document {i}: {str(e)}")
                    continue

        except Exception as e:
            print(f"❌ Error crawling {base_url}: {str(e)}")
            continue

    print(f"\n🎉 Finished! Total successful documents indexed: {successful_uploads}")


# === CALLABLE EXAMPLE ===
if __name__ == "__main__":
    url_array = [
        "https://www.changiairport.com/in/en.html",
        "https://www.jewelchangiairport.com/"
    ]

    asyncio.run(process_urls_to_pinecone(url_array))
