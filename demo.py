#!/usr/bin/env python3
"""
Demo script to show how the Troubleshooting RAG System works
"""

import sys
import os
import yaml
from src.rag_engine import TroubleshootingRAGEngine
from src.data_ingestors import DataIngestors
from src.utils import setup_logging, create_sample_data, validate_config

def main():
    """Demo the RAG system"""
    print("=" * 60)
    print("    TROUBLESHOOTING RAG SYSTEM - DEMO")
    print("=" * 60)
    print()
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Troubleshooting RAG System Demo")
    
    try:
        # Load configuration
        config_path = "config.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize RAG engine
        print("1. Initializing RAG engine...")
        rag_engine = TroubleshootingRAGEngine(config_path)
        print("   ✓ RAG engine ready")
        
        # Initialize data ingestors
        print("2. Initializing data ingestors...")
        data_ingestors = DataIngestors(config)
        print("   ✓ Data ingestors ready")
        
        # Create sample data
        print("3. Creating sample data...")
        create_sample_data()
        print("   ✓ Sample data created")
        
        # Ingest data
        print("4. Ingesting sample data...")
        chunks = data_ingestors.ingest_all_sources("./data/exports")
        print(f"   ✓ Found {len(chunks)} knowledge chunks")
        
        # Add to knowledge base
        print("5. Adding to knowledge base...")
        rag_engine.add_knowledge_chunks(chunks)
        print("   ✓ Knowledge base updated")
        
        # Show statistics
        print("6. Knowledge base statistics:")
        stats = rag_engine.get_collection_stats()
        print(f"   - Total chunks: {stats.get('total_chunks', 0)}")
        print(f"   - Collection: {stats.get('collection_name', 'N/A')}")
        print(f"   - Model: {stats.get('embedding_model', 'N/A')}")
        
        # Demo searches
        print("\n7. Demo searches:")
        print("-" * 30)
        
        test_queries = [
            "login issues",
            "database problems", 
            "slow performance",
            "disk space issues"
        ]
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            results = rag_engine.search_similar(query, n_results=2)
            
            if results:
                for i, result in enumerate(results, 1):
                    source = result['metadata'].get('source', 'Unknown')
                    similarity = 1 - result['distance']
                    print(f"  Result {i}: {source} (similarity: {similarity:.3f})")
                    # Show first 100 chars of content
                    content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                    print(f"    Preview: {content_preview}")
            else:
                print("  No results found")
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE!")
        print("=" * 60)
        print()
        print("WHAT JUST HAPPENED:")
        print("1. ✓ Created sample ticket and Slack data")
        print("2. ✓ Processed the data into knowledge chunks")
        print("3. ✓ Created embeddings for semantic search")
        print("4. ✓ Stored in vector database")
        print("5. ✓ Demonstrated similarity search")
        print()
        print("NEXT STEPS:")
        print("- Replace sample data with your real tickets/Slack exports")
        print("- Use the CLI (python3 cli.py) for interactive use")
        print("- Use the GUI (python3 run.py) for visual interface")
        print("- Add more data sources (logs, documentation)")
        print()
        print("YOUR DATA GOES HERE:")
        print("- CSV tickets: ./data/exports/your_tickets.csv")
        print("- JSON Slack: ./data/exports/your_slack.json")
        print("- Log files: ./data/exports/*.log")
        print("- Docs: ./data/exports/*.md")
        
    except Exception as e:
        print(f"✗ Error during demo: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
