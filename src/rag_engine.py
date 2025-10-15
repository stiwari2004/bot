import os
import yaml
import json
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import pandas as pd
from tqdm import tqdm
import logging

class TroubleshootingRAGEngine:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the RAG engine"""
        self.config = self.load_config(config_path)
        self.setup_logging()
        self.setup_directories()
        self.initialize_components()
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Config file {config_path} not found. Using default config.")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'vector_store': {
                'persist_directory': './data/vector_db',
                'collection_name': 'troubleshooting_knowledge',
                'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2'
            },
            'processing': {
                'chunk_size': 512,
                'chunk_overlap': 50
            }
        }
    
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('troubleshooting_rag.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_directories(self):
        """Create necessary directories"""
        directories = [
            './data',
            './data/exports',
            './data/vector_db',
            './data/logs'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def initialize_components(self):
        """Initialize RAG components"""
        self.logger.info("Initializing RAG components...")
        
        # Initialize embedding model
        self.logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer(
            self.config['vector_store']['embedding_model']
        )
        
        # Initialize vector store
        self.logger.info("Initializing vector store...")
        self.vector_store = chromadb.PersistentClient(
            path=self.config['vector_store']['persist_directory']
        )
        
        # Get or create collection
        try:
            self.collection = self.vector_store.get_collection(
                self.config['vector_store']['collection_name']
            )
            self.logger.info("Loaded existing collection")
        except:
            self.collection = self.vector_store.create_collection(
                self.config['vector_store']['collection_name']
            )
            self.logger.info("Created new collection")
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Split text into chunks"""
        chunk_size = chunk_size or self.config['processing']['chunk_size']
        overlap = overlap or self.config['processing']['chunk_overlap']
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
            
            if start >= len(text):
                break
        
        return chunks
    
    def add_knowledge_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Add knowledge chunks to vector store"""
        if not chunks:
            return 0
        
        self.logger.info(f"Adding {len(chunks)} knowledge chunks...")
        
        # Prepare data for vector store
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk['content'])
            metadatas.append(chunk['metadata'])
            ids.append(chunk['id'])
        
        # Create embeddings
        self.logger.info("Creating embeddings...")
        embeddings = self.embedding_model.encode(documents)
        
        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings.tolist()
        )
        
        self.logger.info(f"Successfully added {len(chunks)} chunks")
        return len(chunks)
    
    def search_similar(self, query: str, n_results: int = 5, filters: Dict = None) -> List[Dict]:
        """Search for similar knowledge chunks"""
        self.logger.info(f"Searching for: {query}")
        
        # Create query embedding
        query_embedding = self.embedding_model.encode([query])
        
        # Search
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results,
            where=filters
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            result = {
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
                'id': results['ids'][0][i]
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        try:
            count = self.collection.count()
            return {
                'total_chunks': count,
                'collection_name': self.config['vector_store']['collection_name'],
                'embedding_model': self.config['vector_store']['embedding_model']
            }
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {e}")
            return {'total_chunks': 0, 'error': str(e)}
    
    def clear_knowledge_base(self):
        """Clear all knowledge from the vector store"""
        try:
            self.vector_store.delete_collection(self.config['vector_store']['collection_name'])
            self.collection = self.vector_store.create_collection(
                self.config['vector_store']['collection_name']
            )
            self.logger.info("Knowledge base cleared successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing knowledge base: {e}")
            return False

