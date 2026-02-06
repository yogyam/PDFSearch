"""
PDF Ingestion Pipeline
Extracts text from PDFs, chunks it, embeds with sentence-transformers, and stores in ChromaDB.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass

import pypdf
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
PDF_DIR = PROJECT_ROOT / "data" / "pdfs"
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"
FAILED_FILES_PATH = PROJECT_ROOT / "data" / "failed_files.txt"

# Chunking config
CHUNK_SIZE_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 50
MIN_CHUNK_TOKENS = 50
APPROX_CHARS_PER_TOKEN = 4  # Rough estimate for English text


@dataclass
class Chunk:
    """Represents a chunk of text from a PDF."""
    text: str
    filename: str
    page_numbers: list[int]  # Pages this chunk spans
    chunk_index: int


def extract_text_from_pdf(pdf_path: Path) -> tuple[str, list[tuple[int, str]]]:
    """
    Extract text from a PDF file.
    
    Returns:
        Tuple of (full_text, list of (page_num, page_text) tuples)
    """
    reader = pypdf.PdfReader(str(pdf_path))
    pages = []
    full_text_parts = []
    
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append((page_num, text))
        full_text_parts.append(text)
    
    return "\n".join(full_text_parts), pages


def chunk_text(text: str, filename: str) -> list[Chunk]:
    """
    Split text into overlapping chunks of approximately CHUNK_SIZE_TOKENS.
    
    Uses character-based splitting with token estimation.
    """
    chunks = []
    
    # Convert token counts to character counts (approximation)
    chunk_size_chars = CHUNK_SIZE_TOKENS * APPROX_CHARS_PER_TOKEN
    overlap_chars = CHUNK_OVERLAP_TOKENS * APPROX_CHARS_PER_TOKEN
    min_chunk_chars = MIN_CHUNK_TOKENS * APPROX_CHARS_PER_TOKEN
    
    # Clean up text
    text = text.strip()
    if len(text) < min_chunk_chars:
        return []  # Too short, skip
    
    start = 0
    chunk_index = 0
    
    while start < len(text):
        end = start + chunk_size_chars
        
        # If not at the end, try to break at a sentence boundary
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            search_start = max(start + chunk_size_chars - 100, start)
            search_end = min(start + chunk_size_chars + 100, len(text))
            search_region = text[search_start:search_end]
            
            # Find last sentence boundary in search region
            for sep in ['. ', '.\n', '? ', '!\n', '! ', '?\n']:
                last_sep = search_region.rfind(sep)
                if last_sep != -1:
                    end = search_start + last_sep + len(sep)
                    break
        
        chunk_text = text[start:end].strip()
        
        # Only keep chunks above minimum length
        if len(chunk_text) >= min_chunk_chars:
            chunks.append(Chunk(
                text=chunk_text,
                filename=filename,
                page_numbers=[1],  # Simplified - could track actual pages
                chunk_index=chunk_index
            ))
            chunk_index += 1
        
        # Move start position with overlap
        start = end - overlap_chars
        if start >= len(text) - min_chunk_chars:
            break  # Remaining text too small for another chunk
    
    return chunks


def ingest_pdfs():
    """Main ingestion pipeline."""
    
    # Ensure directories exist
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize ChromaDB with sentence-transformers embedding
    logger.info("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    # Use sentence-transformers for embeddings
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # Clear existing collection for fresh ingestion
    try:
        existing_collection = client.get_collection(name="pdf_chunks")
        existing_count = existing_collection.count()
        if existing_count > 0:
            logger.info(f"Clearing {existing_count} existing chunks...")
            client.delete_collection(name="pdf_chunks")
    except Exception:
        pass  # Collection doesn't exist yet
    
    # Create collection
    collection = client.get_or_create_collection(
        name="pdf_chunks",
        embedding_function=embedding_fn,
        metadata={"description": "PDF document chunks for semantic search"}
    )
    
    # Scan for PDFs
    pdf_files = list(PDF_DIR.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    if not pdf_files:
        logger.warning(f"No PDFs found in {PDF_DIR}")
        return
    
    # Track failures
    failed_files = []
    all_chunks = []
    
    # Process each PDF
    for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
        try:
            # Extract text
            full_text, pages = extract_text_from_pdf(pdf_path)
            
            if not full_text.strip():
                logger.warning(f"No text extracted from {pdf_path.name}")
                failed_files.append((pdf_path.name, "No text content"))
                continue
            
            # Chunk the text
            chunks = chunk_text(full_text, pdf_path.name)
            
            if not chunks:
                logger.warning(f"No valid chunks from {pdf_path.name}")
                failed_files.append((pdf_path.name, "Text too short"))
                continue
            
            all_chunks.extend(chunks)
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}")
            failed_files.append((pdf_path.name, str(e)))
    
    logger.info(f"Created {len(all_chunks)} chunks from {len(pdf_files) - len(failed_files)} PDFs")
    
    # Add chunks to ChromaDB in batches
    if all_chunks:
        logger.info("Adding chunks to ChromaDB...")
        batch_size = 100
        
        for i in tqdm(range(0, len(all_chunks), batch_size), desc="Storing chunks"):
            batch = all_chunks[i:i + batch_size]
            
            collection.add(
                ids=[f"{chunk.filename}_{chunk.chunk_index}" for chunk in batch],
                documents=[chunk.text for chunk in batch],
                metadatas=[{
                    "filename": chunk.filename,
                    "chunk_index": chunk.chunk_index,
                    "page_numbers": ",".join(map(str, chunk.page_numbers))
                } for chunk in batch]
            )
    
    # Log failures
    if failed_files:
        logger.warning(f"{len(failed_files)} files failed to process")
        with open(FAILED_FILES_PATH, 'w') as f:
            for filename, reason in failed_files:
                f.write(f"{filename}: {reason}\n")
        logger.info(f"Failed files logged to {FAILED_FILES_PATH}")
    
    # Summary
    final_count = collection.count()
    logger.info(f"✓ Ingestion complete: {final_count} chunks stored in ChromaDB")
    logger.info(f"  Database location: {CHROMA_DIR}")


if __name__ == "__main__":
    ingest_pdfs()
