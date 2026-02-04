"""
Golden Test Set for Retrieval Quality
Tests semantic search with 20 query/target pairs. Measures Recall@5 and MRR.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import chromadb

CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"

# Golden test set: (query, expected_pdf_substring)
# Using substrings because some PDFs have suffixes like "_2"
GOLDEN_TEST_SET = [
    # Financial (5 queries)
    ("What was the quarterly revenue growth percentage?", "Q1_2024_Financial_Report"),
    ("What are the company cash reserves?", "Cash_Flow_Statement"),
    ("What is the profit margin for the quarter?", "Profit_Loss_Statement"),
    ("What is the annual budget summary?", "Annual_Budget"),
    ("What does the audit report show?", "Audit_Report"),
    
    # Technical (5 queries)
    ("How does the API handle authentication and JWT?", "API_Documentation"),
    ("What is the database schema and architecture?", "Database_Schema_Design"),
    ("What is the Kubernetes configuration?", "Kubernetes_Configuration"),
    ("How many concurrent users can the system handle?", "Performance_Optimization"),
    ("What is the CI/CD pipeline setup?", "CI_CD_Pipeline"),
    
    # HR (5 queries)
    ("What is the remote work policy for employees?", "Remote_Work_Policy"),
    ("What are the employee benefits and health insurance?", "Benefits_Overview"),
    ("What is the 401k matching and compensation?", "Compensation_Structure"),
    ("What is the new employee onboarding process?", "Onboarding_Checklist"),
    ("What are the termination and exit procedures?", "Termination_Procedures"),
    
    # Legal (3 queries)
    ("What is in the non-disclosure agreement?", "NDA_Standard_Form"),
    ("What are the GDPR compliance requirements?", "GDPR_Compliance"),
    ("What is the software license agreement?", "Software_License_Agreement"),
    
    # Research (2 queries)
    ("What is the market size and growth projection?", "Market_Analysis"),
    ("What is the AI implementation roadmap?", "AI_Implementation_Roadmap"),
]


def calculate_metrics(results: list[tuple[str, str, list[str], bool, int]]) -> dict:
    """
    Calculate Recall@5 and MRR from test results.
    
    Args:
        results: List of (query, expected, top5_results, found, rank)
    
    Returns:
        Dict with metrics
    """
    total = len(results)
    found_count = sum(1 for _, _, _, found, _ in results if found)
    
    # MRR: Mean Reciprocal Rank
    reciprocal_ranks = []
    for _, _, _, found, rank in results:
        if found and rank > 0:
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)
    
    mrr = sum(reciprocal_ranks) / total if total > 0 else 0
    recall_at_5 = found_count / total if total > 0 else 0
    
    return {
        "recall_at_5": recall_at_5,
        "recall_at_5_pct": f"{recall_at_5 * 100:.1f}%",
        "mrr": mrr,
        "found_count": found_count,
        "total": total,
    }


def run_golden_tests():
    """Run all golden test queries and measure metrics."""
    print("=" * 60)
    print("GOLDEN TEST SET - RETRIEVAL QUALITY")
    print("=" * 60)
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection("pdf_chunks")
    
    results = []
    failures = []
    
    print(f"\nRunning {len(GOLDEN_TEST_SET)} test queries...\n")
    
    for i, (query, expected_substring) in enumerate(GOLDEN_TEST_SET, 1):
        # Query ChromaDB
        search_results = collection.query(
            query_texts=[query],
            n_results=5
        )
        
        top5_filenames = [m['filename'] for m in search_results['metadatas'][0]]
        distances = search_results['distances'][0]
        
        # Check if expected file is in top 5
        found = False
        rank = 0
        matched_file = None
        
        for j, filename in enumerate(top5_filenames, 1):
            if expected_substring in filename:
                found = True
                rank = j
                matched_file = filename
                break
        
        results.append((query, expected_substring, top5_filenames, found, rank))
        
        # Print result
        status = "✓" if found else "✗"
        if found:
            print(f"  {status} [{i:2d}] Rank {rank}: {matched_file}")
        else:
            print(f"  {status} [{i:2d}] Expected '{expected_substring}' not in top 5")
            print(f"         Got: {top5_filenames[0]}")
            failures.append((query, expected_substring, top5_filenames))
    
    # Calculate and print metrics
    metrics = calculate_metrics(results)
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Recall@5: {metrics['recall_at_5_pct']} ({metrics['found_count']}/{metrics['total']})")
    print(f"  MRR:      {metrics['mrr']:.3f}")
    
    # Target thresholds
    recall_target = 0.80
    mrr_target = 0.50
    
    print("\n  Targets:")
    recall_status = "✓" if metrics['recall_at_5'] >= recall_target else "✗"
    mrr_status = "✓" if metrics['mrr'] >= mrr_target else "✗"
    print(f"    {recall_status} Recall@5 >= 80%")
    print(f"    {mrr_status} MRR >= 0.50")
    
    # Show failures
    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for query, expected, got in failures:
            print(f"    - Query: '{query[:40]}...'")
            print(f"      Expected: {expected}")
            print(f"      Got: {got[0]}")
    
    return metrics['recall_at_5'] >= recall_target and metrics['mrr'] >= mrr_target


def test_edge_cases():
    """Test edge cases like vague queries and no matches."""
    print("\n" + "=" * 60)
    print("EDGE CASE TESTS")
    print("=" * 60)
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection("pdf_chunks")
    
    edge_cases = [
        ("plans", "Vague query - should return mixed results"),
        ("xyznonexistent123", "Gibberish - should have high distances"),
        ("Q1_2024_Financial_Report", "Exact filename - should match"),
    ]
    
    for query, description in edge_cases:
        results = collection.query(query_texts=[query], n_results=3)
        distances = results['distances'][0]
        filenames = [m['filename'] for m in results['metadatas'][0]]
        
        print(f"\n  Query: '{query}'")
        print(f"  ({description})")
        print(f"  Top result: {filenames[0]} (distance: {distances[0]:.3f})")
        print(f"  Distance range: {min(distances):.3f} - {max(distances):.3f}")


def main():
    """Run all retrieval tests."""
    passed = run_golden_tests()
    test_edge_cases()
    
    print("\n" + "=" * 60)
    if passed:
        print("✓ ALL QUALITY TARGETS MET")
    else:
        print("✗ SOME TARGETS NOT MET - Review failures above")
    print("=" * 60)
    
    return passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
