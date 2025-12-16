"""Script to analyze retrieval accuracy scores after improvements."""

import os
os.environ["CHROMA_HOST"] = "localhost"

from src.config import settings
from src.rag.vectorstore import VectorStore
from src.rag.retriever import F1Retriever

# Initialize
vector_store = VectorStore(
    settings.chroma_persist_dir,
    settings.google_api_key,
    chroma_host=settings.chroma_host,
    chroma_port=settings.chroma_port,
)
retriever = F1Retriever(vector_store)

# Test queries
test_queries = [
    "What is a 5 second penalty?",
    "Why did Max Verstappen get a penalty?",
    "What are track limits?",
    "Explain impeding in F1",
    "What is the difference between reprimand and penalty?",
    "How does the safety car work?",
    "What is a drive through penalty?",
    "Explain DRS rules",
]

print("=" * 80)
print("RETRIEVAL ACCURACY SCORE ANALYSIS (AFTER IMPROVEMENTS)")
print("=" * 80)

all_reg_scores = []
all_stewards_scores = []
all_race_scores = []

for query in test_queries:
    print(f"\n📋 Query: {query}")
    
    # Show expanded query
    expanded = retriever.expand_query(query)
    if expanded != query:
        print(f"   Expanded: {expanded[:80]}...")
    print("-" * 60)
    
    # Get context with all improvements
    query_context = retriever.extract_race_context(query)
    context = retriever.retrieve(query, top_k=5, query_context=query_context)
    
    # Collect scores
    for r in context.regulations:
        all_reg_scores.append(r.score)
    for r in context.stewards_decisions:
        all_stewards_scores.append(r.score)
    for r in context.race_data:
        all_race_scores.append(r.score)
    
    # Show top 3 from each
    if context.regulations:
        print(f"  📜 Regulations (top 3):")
        for i, result in enumerate(context.regulations[:3]):
            print(f"    {i+1}. Score: {result.score:.4f}")
    
    if context.stewards_decisions:
        print(f"  ⚖️ Stewards (top 3):")
        for i, result in enumerate(context.stewards_decisions[:3]):
            print(f"    {i+1}. Score: {result.score:.4f}")

print("\n" + "=" * 80)
print("SUMMARY - CURRENT ACCURACY SCORES")
print("=" * 80)

if all_reg_scores:
    print(f"\nRegulations:")
    print(f"  Average Score: {sum(all_reg_scores)/len(all_reg_scores):.4f}")
    print(f"  Min Score: {min(all_reg_scores):.4f}")
    print(f"  Max Score: {max(all_reg_scores):.4f}")
    print(f"  Results >= 0.7: {len([s for s in all_reg_scores if s >= 0.7])}/{len(all_reg_scores)}")
    print(f"  Results >= 0.8: {len([s for s in all_reg_scores if s >= 0.8])}/{len(all_reg_scores)}")

if all_stewards_scores:
    print(f"\nStewards Decisions:")
    print(f"  Average Score: {sum(all_stewards_scores)/len(all_stewards_scores):.4f}")
    print(f"  Min Score: {min(all_stewards_scores):.4f}")
    print(f"  Max Score: {max(all_stewards_scores):.4f}")
    print(f"  Results >= 0.7: {len([s for s in all_stewards_scores if s >= 0.7])}/{len(all_stewards_scores)}")
    print(f"  Results >= 0.8: {len([s for s in all_stewards_scores if s >= 0.8])}/{len(all_stewards_scores)}")

if all_race_scores:
    print(f"\nRace Data:")
    print(f"  Average Score: {sum(all_race_scores)/len(all_race_scores):.4f}")
    print(f"  Min Score: {min(all_race_scores):.4f}")
    print(f"  Max Score: {max(all_race_scores):.4f}")
    print(f"  Results >= 0.7: {len([s for s in all_race_scores if s >= 0.7])}/{len(all_race_scores)}")
    print(f"  Results >= 0.8: {len([s for s in all_race_scores if s >= 0.8])}/{len(all_race_scores)}")

# Overall
all_scores = all_reg_scores + all_stewards_scores + all_race_scores
print(f"\n{'='*80}")
print(f"OVERALL METRICS:")
print(f"  Total Results: {len(all_scores)}")
print(f"  Average Score: {sum(all_scores)/len(all_scores):.4f}")
print(f"  Min Score: {min(all_scores):.4f}")
print(f"  Max Score: {max(all_scores):.4f}")
print(f"  Results >= 0.7: {len([s for s in all_scores if s >= 0.7])}/{len(all_scores)} ({100*len([s for s in all_scores if s >= 0.7])/len(all_scores):.1f}%)")
print(f"  Results >= 0.8: {len([s for s in all_scores if s >= 0.8])}/{len(all_scores)} ({100*len([s for s in all_scores if s >= 0.8])/len(all_scores):.1f}%)")
print(f"  Results >= 0.9: {len([s for s in all_scores if s >= 0.9])}/{len(all_scores)} ({100*len([s for s in all_scores if s >= 0.9])/len(all_scores):.1f}%)")

print(f"\n{'='*80}")
print("GAP ANALYSIS TO REACH 0.9 AVERAGE")
print("=" * 80)
current_avg = sum(all_scores)/len(all_scores)
gap = 0.9 - current_avg
print(f"  Current Average: {current_avg:.4f}")
print(f"  Target Average: 0.9000")
print(f"  Gap: {gap:.4f} ({gap*100:.1f}%)")

print(f"\n  WHAT'S NEEDED TO REACH 0.9:")
print(f"  ─────────────────────────────")
print(f"  1. Fine-tuned embeddings on F1 domain data (~+15-25% improvement)")
print(f"  2. Cross-encoder re-ranking model (~+10-15% improvement)")
print(f"  3. Larger/better embedding model (e.g., text-embedding-3-large)")
print(f"  4. More structured metadata for filtering")
print(f"  5. LLM-based relevance scoring post-retrieval")

print("\n" + "=" * 80)
