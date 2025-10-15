#!/usr/bin/env python3
"""
Troubleshooting RAG System - Main Application
"""

import sys
import os

# Check Python version
if sys.version_info < (3, 7):
    print("Error: Python 3.7 or higher is required")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Please install it with: pip install pyyaml")
    sys.exit(1)

try:
    from src.rag_engine import TroubleshootingRAGEngine
    from src.data_ingestors import DataIngestors
    from src.gui import TroubleshootingRAGGUI
    from src.utils import setup_logging, create_sample_data, validate_config
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

def main():
    """Main application entry point"""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Troubleshooting RAG System")
    
    try:
        # Load configuration
        config_path = "config.yaml"
        if not os.path.exists(config_path):
            logger.error(f"Configuration file {config_path} not found")
            print(f"Error: Configuration file {config_path} not found")
            print("Please create config.yaml or run with --create-config")
            return 1
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if not validate_config(config):
            logger.error("Invalid configuration")
            return 1
        
        # Initialize RAG engine
        logger.info("Initializing RAG engine...")
        rag_engine = TroubleshootingRAGEngine(config_path)
        
        # Initialize data ingestors
        logger.info("Initializing data ingestors...")
        data_ingestors = DataIngestors(config)
        
        # Check if we should create sample data
        if len(sys.argv) > 1 and sys.argv[1] == '--create-sample':
            logger.info("Creating sample data...")
            create_sample_data()
            print("Sample data created. You can now run the application.")
            return 0
        
        # Start GUI
        logger.info("Starting GUI...")
        gui = TroubleshootingRAGGUI(rag_engine, data_ingestors)
        gui.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\nApplication interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
