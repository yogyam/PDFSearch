"""
Unit Tests for Ingestion Pipeline
Tests extraction, chunking, embedding, and storage components.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pypdf
import chromadb
from ingest import extract_text_from_pdf, chunk_text, Chunk

# Paths
PDF_DIR = PROJECT_ROOT / "data" / "pdfs"
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"


def test_pdf_extraction():
    """Test that we can extract text from PDFs."""
    print("\n=== Test 1: PDF Extraction ===")
    
    pdf_files = list(PDF_DIR.glob("*.pdf"))[:5]  # Test first 5
    passed = 0
    failed = 0
    
    for pdf_path in pdf_files:
        try:
            full_text, pages = extract_text_from_pdf(pdf_path)
            
            if len(full_text) > 100:
                print(f"  ✓ {pdf_path.name}: {len(full_text)} chars extracted")
                passed += 1
            else:
                print(f"  ✗ {pdf_path.name}: Only {len(full_text)} chars (too short)")
                failed += 1
        except Exception as e:
            print(f"  ✗ {pdf_path.name}: Error - {e}")
            failed += 1
    
    print(f"\n  Result: {passed}/{passed+failed} passed")
    return failed == 0


def test_chunking():
    """Test that chunking produces valid chunks with proper sizes."""
    print("\n=== Test 2: Chunking ===")
    
    # Get a sample PDF
    pdf_path = list(PDF_DIR.glob("*.pdf"))[0]
    full_text, _ = extract_text_from_pdf(pdf_path)
    
    chunks = chunk_text(full_text, pdf_path.name)
    
    print(f"  Input text length: {len(full_text)} chars")
    print(f"  Number of chunks: {len(chunks)}")
    
    if len(chunks) == 0:
        print(f"  ✗ No chunks created")
        return False
    
    # Check chunk properties
    all_valid = True
    for i, chunk in enumerate(chunks):
        # Check minimum length (50 tokens * ~4 chars = ~200 chars)
        if len(chunk.text) < 200:
            print(f"  ✗ Chunk {i} too short: {len(chunk.text)} chars")
            all_valid = False
        
        # Check metadata
        if not chunk.filename:
            print(f"  ✗ Chunk {i} missing filename")
            all_valid = False
    
    if all_valid:
        print(f"  ✓ All {len(chunks)} chunks valid")
        print(f"  ✓ Chunk sizes: {[len(c.text) for c in chunks]} chars")
    
    return all_valid


def test_chromadb_storage():
    """Test that ChromaDB has data with correct structure."""
    print("\n=== Test 3: ChromaDB Storage ===")
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    try:
        collection = client.get_collection("pdf_chunks")
    except Exception as e:
        print(f"  ✗ Collection not found: {e}")
        return False
    
    count = collection.count()
    print(f"  Total chunks in DB: {count}")
    
    if count == 0:
        print(f"  ✗ No chunks in database")
        return False
    
    # Check sample data structure
    sample = collection.get(limit=1, include=["documents", "metadatas", "embeddings"])
    
    checks = [
        ("Has document", len(sample['documents']) > 0 and len(sample['documents'][0]) > 0),
        ("Has metadata", len(sample['metadatas']) > 0),
        ("Has filename in metadata", 'filename' in sample['metadatas'][0]),
        ("Has chunk_index in metadata", 'chunk_index' in sample['metadatas'][0]),
        ("Has embeddings", sample['embeddings'] is not None and len(sample['embeddings'][0]) > 0),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print(f"  ✓ Embedding dimension: {len(sample['embeddings'][0])}")
    
    return all_passed


def test_metadata_completeness():
    """Test that all chunks have complete metadata."""
    print("\n=== Test 4: Metadata Completeness ===")
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection("pdf_chunks")
    
    # Get all metadata
    all_data = collection.get(include=["metadatas"])
    
    missing_fields = []
    required_fields = ['filename', 'chunk_index', 'page_numbers']
    
    for i, meta in enumerate(all_data['metadatas']):
        for field in required_fields:
            if field not in meta or meta[field] is None:
                missing_fields.append(f"Chunk {i} missing {field}")
    
    if missing_fields:
        print(f"  ✗ {len(missing_fields)} missing fields:")
        for msg in missing_fields[:5]:  # Show first 5
            print(f"    - {msg}")
        return False
    
    print(f"  ✓ All {len(all_data['metadatas'])} chunks have complete metadata")
    
    # Check filename distribution
    filenames = set(m['filename'] for m in all_data['metadatas'])
    print(f"  ✓ Chunks from {len(filenames)} unique PDFs")
    
    return True


def test_no_duplicate_ids():
    """Test that there are no duplicate chunk IDs."""
    print("\n=== Test 5: No Duplicate IDs ===")
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection("pdf_chunks")
    
    all_ids = collection.get()['ids']
    unique_ids = set(all_ids)
    
    if len(all_ids) != len(unique_ids):
        duplicates = len(all_ids) - len(unique_ids)
        print(f"  ✗ Found {duplicates} duplicate IDs")
        return False
    
    print(f"  ✓ All {len(all_ids)} IDs are unique")
    return True


def main():
    """Run all unit tests."""
    print("=" * 60)
    print("INGESTION PIPELINE UNIT TESTS")
    print("=" * 60)
    
    tests = [
        ("PDF Extraction", test_pdf_extraction),
        ("Chunking", test_chunking),
        ("ChromaDB Storage", test_chromadb_storage),
        ("Metadata Completeness", test_metadata_completeness),
        ("No Duplicate IDs", test_no_duplicate_ids),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"\n  ✗ Test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
