#!/usr/bin/env python3
"""
Simple script to upload and process a CSV file
"""

import sys
import os
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def upload_csv():
    """Upload and process a CSV file"""
    print("CSV File Uploader")
    print("=" * 30)
    
    # Get CSV file path
    csv_file = input("Enter path to your CSV file: ").strip()
    
    if not os.path.exists(csv_file):
        print(f"✗ File not found: {csv_file}")
        return
    
    try:
        # Read CSV
        print(f"Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        print(f"✓ Found {len(df)} rows")
        
        # Show columns
        print(f"Columns: {list(df.columns)}")
        
        # Check required columns
        required_cols = ['id', 'description', 'resolution']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"✗ Missing required columns: {missing_cols}")
            print("Required columns: id, description, resolution")
            return
        
        # Copy to exports directory
        print("Copying to exports directory...")
        os.makedirs("./data/exports", exist_ok=True)
        
        import shutil
        dest_file = "./data/exports/uploaded_tickets.csv"
        shutil.copy2(csv_file, dest_file)
        print(f"✓ Copied to {dest_file}")
        
        # Process with RAG system
        print("Processing with RAG system...")
        
        from src.rag_engine import TroubleshootingRAGEngine
        from src.data_ingestors import DataIngestors
        import yaml
        
        # Load config and initialize
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        rag_engine = TroubleshootingRAGEngine("config.yaml")
        data_ingestors = DataIngestors(config)
        
        # Ingest data
        chunks = data_ingestors.ingest_all_sources("./data/exports")
        
        if chunks:
            rag_engine.add_knowledge_chunks(chunks)
            print(f"✓ Successfully processed {len(chunks)} knowledge chunks")
            
            # Test search
            print("\nTesting search...")
            results = rag_engine.search_similar("login issues", n_results=2)
            print(f"✓ Search working - found {len(results)} results")
            
            print("\n" + "=" * 50)
            print("✓ CSV UPLOAD SUCCESSFUL!")
            print("=" * 50)
            print("\nYour data is now in the knowledge base!")
            print("You can search it using:")
            print("- python3 simple_gui.py")
            print("- python3 cli.py")
        else:
            print("✗ No data processed")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    upload_csv()

