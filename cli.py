#!/usr/bin/env python3
"""
Command Line Interface for Troubleshooting RAG System
"""

import sys
import os
import yaml
from src.rag_engine import TroubleshootingRAGEngine
from src.data_ingestors import DataIngestors
from src.utils import setup_logging, create_sample_data, validate_config

def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("    TROUBLESHOOTING RAG SYSTEM - COMMAND LINE")
    print("=" * 60)
    print()

def print_menu():
    """Print main menu"""
    print("MAIN MENU:")
    print("1. Create sample data")
    print("2. Ingest data from directory")
    print("3. Search knowledge base")
    print("4. Show statistics")
    print("5. Clear knowledge base")
    print("6. Exit")
    print()

def create_sample_data_cli():
    """Create sample data via CLI"""
    print("Creating sample data...")
    try:
        create_sample_data()
        print("✓ Sample data created successfully!")
        print("  - sample_tickets.csv")
        print("  - sample_slack.json")
        print("  Location: ./data/exports/")
    except Exception as e:
        print(f"✗ Error creating sample data: {e}")

def ingest_data_cli(rag_engine, data_ingestors):
    """Ingest data via CLI"""
    print("Data Ingestion")
    print("-" * 20)
    
    # Check if sample data exists
    sample_tickets = "./data/exports/sample_tickets.csv"
    sample_slack = "./data/exports/sample_slack.json"
    
    if os.path.exists(sample_tickets) and os.path.exists(sample_slack):
        print("Found sample data files:")
        print(f"  - {sample_tickets}")
        print(f"  - {sample_slack}")
        
        use_sample = input("Use sample data? (y/n): ").lower().strip()
        if use_sample == 'y':
            data_directory = "./data/exports"
        else:
            data_directory = input("Enter path to your data directory: ").strip()
    else:
        data_directory = input("Enter path to your data directory: ").strip()
    
    if not os.path.exists(data_directory):
        print(f"✗ Directory not found: {data_directory}")
        return
    
    print(f"Ingesting data from: {data_directory}")
    try:
        chunks = data_ingestors.ingest_all_sources(data_directory)
        
        if chunks:
            rag_engine.add_knowledge_chunks(chunks)
            print(f"✓ Successfully ingested {len(chunks)} knowledge chunks")
        else:
            print("✗ No data found to ingest")
            print("Make sure your directory contains:")
            print("  - CSV files with ticket data")
            print("  - JSON files with Slack data")
            print("  - LOG files with error logs")
            print("  - MD/TXT files with documentation")
    except Exception as e:
        print(f"✗ Error during ingestion: {e}")

def search_cli(rag_engine):
    """Search knowledge base via CLI"""
    print("Knowledge Base Search")
    print("-" * 25)
    
    query = input("Enter your search query: ").strip()
    if not query:
        print("✗ Please enter a search query")
        return
    
    try:
        print(f"Searching for: {query}")
        results = rag_engine.search_similar(query, n_results=5)
        
        if results:
            print(f"\nFound {len(results)} results:")
            print("=" * 60)
            
            for i, result in enumerate(results, 1):
                print(f"\nRESULT {i}:")
                print(f"Source: {result['metadata'].get('source', 'Unknown')}")
                print(f"Similarity: {1 - result['distance']:.3f}")
                print(f"Content:")
                print("-" * 40)
                print(result['content'])
                print("-" * 40)
        else:
            print("✗ No results found")
            print("Try:")
            print("  - Different keywords")
            print("  - Ingesting more data first")
    except Exception as e:
        print(f"✗ Error during search: {e}")

def show_stats_cli(rag_engine):
    """Show statistics via CLI"""
    print("Knowledge Base Statistics")
    print("-" * 30)
    
    try:
        stats = rag_engine.get_collection_stats()
        print(f"Total Knowledge Chunks: {stats.get('total_chunks', 0)}")
        print(f"Collection Name: {stats.get('collection_name', 'N/A')}")
        print(f"Embedding Model: {stats.get('embedding_model', 'N/A')}")
        
        if stats.get('total_chunks', 0) == 0:
            print("\n💡 No data in knowledge base yet!")
            print("   Try option 1 (Create sample data) or option 2 (Ingest data)")
    except Exception as e:
        print(f"✗ Error getting statistics: {e}")

def clear_knowledge_base_cli(rag_engine):
    """Clear knowledge base via CLI"""
    print("Clear Knowledge Base")
    print("-" * 25)
    
    confirm = input("Are you sure you want to clear all knowledge? (yes/no): ").lower().strip()
    if confirm == 'yes':
        try:
            rag_engine.clear_knowledge_base()
            print("✓ Knowledge base cleared successfully")
        except Exception as e:
            print(f"✗ Error clearing knowledge base: {e}")
    else:
        print("Operation cancelled")

def main():
    """Main CLI application"""
    print_banner()
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Troubleshooting RAG System CLI")
    
    try:
        # Load configuration
        config_path = "config.yaml"
        if not os.path.exists(config_path):
            print(f"✗ Configuration file {config_path} not found")
            return 1
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if not validate_config(config):
            print("✗ Invalid configuration")
            return 1
        
        # Initialize RAG engine
        print("Initializing RAG engine...")
        rag_engine = TroubleshootingRAGEngine(config_path)
        
        # Initialize data ingestors
        print("Initializing data ingestors...")
        data_ingestors = DataIngestors(config)
        
        print("✓ System ready!")
        print()
        
        # Main loop
        while True:
            try:
                print_menu()
                choice = input("Enter your choice (1-6): ").strip()
                
                if choice == '1':
                    create_sample_data_cli()
                elif choice == '2':
                    ingest_data_cli(rag_engine, data_ingestors)
                elif choice == '3':
                    search_cli(rag_engine)
                elif choice == '4':
                    show_stats_cli(rag_engine)
                elif choice == '5':
                    clear_knowledge_base_cli(rag_engine)
                elif choice == '6':
                    print("Goodbye!")
                    break
                else:
                    print("✗ Invalid choice. Please enter 1-6.")
                
                print("\n" + "=" * 60 + "\n")
                
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
        
    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user")
        return 0
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
