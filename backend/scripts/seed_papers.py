import httpx
import asyncio
import time

TOPICS = [
    "Machine Learning", "Quantum Computing", "CRISPR Gene Editing", 
    "Climate Change Mitigation", "Neuroscience and Brain Mapping",
    "Space Exploration and Mars", "Blockchain and Cryptography",
    "Cybersecurity and Privacy", "Renewable Energy and Solar",
    "Synthetic Biology", "Autonomous Vehicles", "Materials Science",
    "Internet of Things", "Augmented Reality", "Digital Health",
    "Edge Computing", "Big Data Analytics", "Robotics and Automation",
    "Nanotechnology", "Natural Language Processing", "Computer Vision",
    "Distributed Systems", "Sustainable Agriculture", "Deep Learning",
    "Reinforcement Learning", "Graph Neural Networks", "Large Language Models",
    "Quantum Cryptography", "Bioinformatics", "Smart Cities", "FinTech",
    "Green Energy", "Nuclear Fusion", "Exoplanets", "Genomics",
    "Wearable Technology", "Cloud Computing", "Software Engineering",
    "Operating Systems", "Human-Computer Interaction"
]

API_URL = "http://localhost:8000/api/papers/ingest"

async def seed():
    async with httpx.AsyncClient(timeout=60) as client:
        total_ingested = 0
        for topic in TOPICS:
            if total_ingested >= 500:
                break
            
            print(f"Ingesting papers for: {topic}...")
            try:
                payload = {
                    "query": topic,
                    "limit": 25,
                    "sources": ["semantic_scholar", "arxiv"]
                }
                response = await client.post(API_URL, json=payload)
                if response.status_code == 429:
                    print(f"  ! Rate limited (429) for {topic}. Sleeping for 15s...")
                    await asyncio.sleep(15)
                    continue
                
                response.raise_for_status()
                data = response.json()
                new_papers = data.get("new", 0)
                total_ingested += new_papers
                print(f"  -> Added {new_papers} new papers. Total: {total_ingested}")
                
                # Sleep to be nice to APIs
                await asyncio.sleep(3)
            except Exception as e:
                print(f"  X Error for {topic}: {e}")
                await asyncio.sleep(10)

        print(f"\nSeeding complete! Added ~{total_ingested} papers.")

if __name__ == "__main__":
    asyncio.run(seed())
