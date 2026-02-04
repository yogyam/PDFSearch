# System Design: Cost-Optimized Local PDF Search

## 1. Problem Statement & Constraints
**Goal**: Build a system to search through ~100 locally stored PDFs and return accurate answers with source citations.
**Key Constraints**:
1.  **Cost Optimization**: Minimize LLM API calls. Use local models where possible.
2.  **Local Execution**: The system runs locally on a Mac.
3.  **Simplicity**: With ~100 docs, avoid over-engineering. Keep the pipeline lean.
4.  **Accuracy**: High accuracy is prioritized over ultra-low latency (<500ms is not required).

---

## 2. High-Level Architecture
We utilize a **Retrieve-Then-Read** architecture with direct chunk search and cross-encoder reranking.

```mermaid
graph TD
    UserQuery[User Query] --> Embed[Embed Query\n(all-MiniLM-L6-v2)]
    
    subgraph "Stage 1: Chunk Retrieval (Top-K=20)"
        Embed --> ChunkSearch[Vector Search: All Content Chunks]
        ChunkSearch --> CandidateChunks[20 Candidate Chunks]
    end
    
    subgraph "Stage 2: Reranking"
        CandidateChunks --> Rerank[Cross-Encoder Reranking\n(ms-marco-MiniLM-L-6-v2)]
        Rerank --> TopChunks[Top 5 Final Chunks]
    end
    
    subgraph "Stage 3: Generation"
        TopChunks --> LLM[LLM Generation\n(gpt-4o-mini)]
        LLM --> FinalResult[Answer + Citations]
    end
```

---

## 3. Technology Stack

| Component | Choice | Justification |
|-----------|--------|---------------|
| **Language** | `Python` | Rich ecosystem for NLP/ML (Pypdf, Chroma, etc). |
| **Parsing** | `pypdf` | **Local & Free**. Sufficient for text-heavy docs. |
| **Vector Store** | `ChromaDB` | **Serverless Local Storage**. SQLite-based, no Docker needed. |
| **Embeddings** | `all-MiniLM-L6-v2` | Open source, runs locally, $0 cost. |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Drastically improves precision. $0 cost (local). |
| **LLM** | `gpt-4o-mini` | Cheap (~$0.01/query), capable for RAG. |

---

## 4. Key Design Decisions & Trade-offs

### A. Direct Chunk Search (No Document-Level Filtering)
*   **Why Skip 2-Stage Filtering?** With only ~100 docs (~500-1000 chunks), direct chunk search is efficient. The reranker handles noise well.
*   **Benefit**: Simpler pipeline, no LLM summarization cost, no risk of filtering out relevant content.

### B. Chunking Strategy
*   **Decision**: **Fixed Size (512 tokens) with Overlap (50 tokens)**.
*   **Why**: Overlap ensures sentences aren't cut at boundaries. Simple and robust for varied PDF formats.

### C. Reranking with Cross-Encoders
*   **Decision**: Add a Reranker step (bi-encoder retrieval → cross-encoder scoring).
*   **Trade-off**: Adds ~200ms of latency per query.
*   **Justification**: Accuracy is prioritized. Cross-encoders "read" query+text together for much better relevance scoring.

### D. No LLM Summarization During Ingestion
*   **Decision**: Skip generating summaries for each document.
*   **Why**: 
    - Saves ~$0.20-2 in API costs
    - No information loss (full content is searchable)
    - Faster ingestion (no API calls)
    - For 100 docs, document-level filtering isn't necessary

---

## 5. Pipeline Details

### Ingestion (One-Time)
1.  **Scan**: Walk local `data/pdfs/` folder.
2.  **Extract**: `pypdf` extracts raw text from each PDF.
3.  **Chunk**: Split text into 512-token chunks with 50-token overlap.
    - Discard chunks < 50 tokens (headers/footers).
4.  **Embed**: Use `all-MiniLM-L6-v2` to embed each chunk.
5.  **Store**: Save vectors + metadata (filename, page number, chunk index) in ChromaDB.

### Query Handling (Run Time)
1.  **Embed**: Embed user query with same model.
2.  **Search**: Vector search all chunks → Top 20 candidates.
3.  **Rerank**: Score (Query, Chunk) pairs with cross-encoder → Top 5.
4.  **Generate**: Send top 5 chunks to `gpt-4o-mini` with prompt:
    - *"Answer the user query using strictly the context below. Cite the filename for every statement."*

---

## 6. Handling Edge Cases

| Scenario | System Behavior |
|----------|-----------------|
| **Vague Query** ("plans") | Return results with lower confidence. User can clarify. |
| **Zero Matches** | If max score < threshold, return "No relevant information found." |
| **Corrupt PDF** | Log to `failed_files.txt` and continue. Don't crash. |
| **Short Chunks** | Discard chunks < 50 tokens to avoid matching headers/footers. |

---

## 7. Evaluation Strategy
**Method**: **Golden Test Set** (Ground Truth).

1.  **Create Dataset**: Curate 20 pairs of `(Query, Target_PDF, Target_Chunk_Text)`.
2.  **Metrics**:
    *   **Recall@5**: Does the correct chunk appear in top 5 results?
    *   **MRR (Mean Reciprocal Rank)**: Measures ranking quality (1.0 if correct chunk is #1, 0.5 if #2, etc.).
