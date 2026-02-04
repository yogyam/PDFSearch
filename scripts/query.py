"""
Query Pipeline
Handles user queries: search → rerank → generate answer with citations.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

import chromadb
from sentence_transformers import CrossEncoder
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"

# Config
TOP_K_SEARCH = 20  # Initial retrieval
TOP_K_RERANK = 5   # After reranking
DISTANCE_THRESHOLD = 1.0  # Max distance for "no results" detection


@dataclass
class SearchResult:
    """A search result with metadata."""
    text: str
    filename: str
    chunk_index: int
    distance: float  # Lower is better (from vector search)
    rerank_score: float = 0.0  # Higher is better (from cross-encoder)


class QueryPipeline:
    """Handles the full query pipeline: search → rerank → generate."""
    
    def __init__(self, openai_api_key: str = None):
        """Initialize the query pipeline."""
        # ChromaDB
        logger.info("Loading ChromaDB...")
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = self.client.get_collection("pdf_chunks")
        
        # Cross-encoder for reranking (local)
        logger.info("Loading cross-encoder model...")
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # OpenAI client for generation
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized")
        else:
            self.openai_client = None
            logger.warning("No OpenAI API key - generation disabled")
    
    def search(self, query: str, top_k: int = TOP_K_SEARCH) -> list[SearchResult]:
        """
        Stage 1: Vector search to get candidate chunks.
        
        Args:
            query: User query
            top_k: Number of results to retrieve
            
        Returns:
            List of SearchResult objects, sorted by distance (best first)
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        search_results = []
        for i in range(len(results['documents'][0])):
            search_results.append(SearchResult(
                text=results['documents'][0][i],
                filename=results['metadatas'][0][i]['filename'],
                chunk_index=results['metadatas'][0][i]['chunk_index'],
                distance=results['distances'][0][i],
            ))
        
        return search_results
    
    def rerank(self, query: str, results: list[SearchResult], top_k: int = TOP_K_RERANK) -> list[SearchResult]:
        """
        Stage 2: Rerank results using cross-encoder.
        
        The cross-encoder reads (query, document) pairs together for better relevance scoring.
        
        Args:
            query: User query
            results: Candidate results from vector search
            top_k: Number of top results to return after reranking
            
        Returns:
            Top K results, sorted by rerank score (best first)
        """
        if not results:
            return []
        
        # Create pairs for cross-encoder
        pairs = [(query, r.text) for r in results]
        
        # Score all pairs
        scores = self.reranker.predict(pairs)
        
        # Add scores to results
        for i, result in enumerate(results):
            result.rerank_score = float(scores[i])
        
        # Sort by rerank score (higher is better) and return top K
        results.sort(key=lambda r: r.rerank_score, reverse=True)
        return results[:top_k]
    
    def generate(self, query: str, results: list[SearchResult]) -> str:
        """
        Stage 3: Generate answer using LLM with context from top results.
        
        Args:
            query: User query
            results: Top reranked results
            
        Returns:
            Generated answer with citations
        """
        if not self.openai_client:
            return "[Error: OpenAI API key not configured]"
        
        if not results:
            return "No relevant information found in the documents."
        
        # Check if best result is too far (likely no good match)
        if results[0].distance > DISTANCE_THRESHOLD and results[0].rerank_score < 0:
            return "No relevant information found in the documents."
        
        # Build context from results
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"[Source {i}: {result.filename}]\n{result.text}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate with LLM
        system_prompt = """You are a helpful assistant that answers questions based on provided document excerpts.

Rules:
1. Answer ONLY using information from the provided context
2. Cite the source filename for every statement (e.g., "According to Report.pdf, ...")
3. If the context doesn't contain enough information, say so
4. Be concise and direct"""

        user_prompt = f"""Context from documents:

{context}

---

Question: {query}

Please answer the question using only the information provided above. Cite the filename for each statement."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"[Error generating response: {e}]"
    
    def query(self, user_query: str, verbose: bool = False) -> dict:
        """
        Run the full query pipeline.
        
        Args:
            user_query: The user's question
            verbose: If True, include intermediate results
            
        Returns:
            Dict with 'answer' and optionally 'search_results' and 'reranked_results'
        """
        # Stage 1: Search
        search_results = self.search(user_query)
        if verbose:
            logger.info(f"Search returned {len(search_results)} results")
        
        # Stage 2: Rerank
        reranked_results = self.rerank(user_query, search_results)
        if verbose:
            logger.info(f"Top result after rerank: {reranked_results[0].filename} (score: {reranked_results[0].rerank_score:.3f})")
        
        # Stage 3: Generate
        answer = self.generate(user_query, reranked_results)
        
        result = {"answer": answer}
        
        if verbose:
            result["search_results"] = [
                {"filename": r.filename, "distance": r.distance}
                for r in search_results[:5]
            ]
            result["reranked_results"] = [
                {"filename": r.filename, "score": r.rerank_score, "text_preview": r.text[:100]}
                for r in reranked_results
            ]
        
        return result


def main():
    """Interactive query mode."""
    print("=" * 60)
    print("PDF SEARCH - Query Pipeline")
    print("=" * 60)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  OPENAI_API_KEY not set. Set it to enable LLM generation:")
        print("   export OPENAI_API_KEY='your-key-here'\n")
    
    pipeline = QueryPipeline()
    
    print("\nReady! Enter your questions (or 'quit' to exit)\n")
    
    while True:
        try:
            query = input("Query: ").strip()
            
            if query.lower() in ('quit', 'exit', 'q'):
                print("Goodbye!")
                break
            
            if not query:
                continue
            
            print("\nSearching...\n")
            result = pipeline.query(query, verbose=True)
            
            print("-" * 40)
            print("ANSWER:")
            print("-" * 40)
            print(result["answer"])
            print()
            
            if "reranked_results" in result:
                print("Sources used:")
                for r in result["reranked_results"]:
                    print(f"  - {r['filename']} (score: {r['score']:.3f})")
            print()
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
