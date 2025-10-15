#!/usr/bin/env python3
"""
Test script to verify the system works
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_system():
    """Test the system components"""
    print("Testing Troubleshooting RAG System...")
    print("=" * 50)
    
    try:
        # Test 1: Import modules
        print("1. Testing imports...")
        from src.rag_engine import TroubleshootingRAGEngine
        from src.data_ingestors import DataIngestors
        import yaml
        print("   ✓ All imports successful")
        
        # Test 2: Load config
        print("2. Testing configuration...")
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        print("   ✓ Configuration loaded")
        
        # Test 3: Initialize RAG engine
        print("3. Testing RAG engine...")
        rag_engine = TroubleshootingRAGEngine("config.yaml")
        print("   ✓ RAG engine initialized")
        
        # Test 4: Initialize data ingestors
        print("4. Testing data ingestors...")
        data_ingestors = DataIngestors(config)
        print("   ✓ Data ingestors initialized")
        
        # Test 5: Check if sample data exists
        print("5. Checking sample data...")
        sample_csv = "./data/exports/sample_tickets.csv"
        sample_json = "./data/exports/sample_slack.json"
        
        if os.path.exists(sample_csv) and os.path.exists(sample_json):
            print("   ✓ Sample data exists")
        else:
            print("   ! Sample data not found - run demo.py first")
        
        # Test 6: Test search (if data exists)
        stats = rag_engine.get_collection_stats()
        if stats.get('total_chunks', 0) > 0:
            print("6. Testing search...")
            results = rag_engine.search_similar("login issues", n_results=2)
            print(f"   ✓ Search working - found {len(results)} results")
        else:
            print("6. No data to test search with")
        
        print("\n" + "=" * 50)
        print("✓ SYSTEM TEST PASSED!")
        print("=" * 50)
        print("\nYou can now use:")
        print("- python3 simple_gui.py (for GUI with file upload)")
        print("- python3 cli.py (for command line interface)")
        print("- python3 demo.py (to see the system in action)")
        
        return True
        
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_system()
    sys.exit(0 if success else 1)

