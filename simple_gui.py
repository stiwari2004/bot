#!/usr/bin/env python3
"""
Simple GUI for Troubleshooting RAG System - Fixed for macOS
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.rag_engine import TroubleshootingRAGEngine
from src.data_ingestors import DataIngestors
import yaml

class SimpleTroubleshootingGUI:
    def __init__(self):
        self.rag_engine = None
        self.data_ingestors = None
        self.setup_gui()
        self.initialize_system()
    
    def setup_gui(self):
        """Setup the GUI"""
        # Create main window
        self.root = tk.Tk()
        self.root.title("Troubleshooting RAG System")
        self.root.geometry("900x700")
        self.root.configure(bg='white')
        
        # Main container
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(main_frame, text="Troubleshooting RAG System", 
                        font=("Arial", 18, "bold"), bg='white')
        title.pack(pady=(0, 20))
        
        # Status
        self.status_var = tk.StringVar()
        self.status_var.set("Initializing...")
        status_label = tk.Label(main_frame, textvariable=self.status_var, 
                               font=("Arial", 10), bg='white', fg='blue')
        status_label.pack(pady=(0, 20))
        
        # File Upload Section
        upload_frame = tk.LabelFrame(main_frame, text="Upload Data Files", 
                                   font=("Arial", 12, "bold"), bg='white')
        upload_frame.pack(fill=tk.X, pady=(0, 20))
        
        # CSV Upload
        csv_frame = tk.Frame(upload_frame, bg='white')
        csv_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(csv_frame, text="Upload CSV Tickets:", font=("Arial", 10), bg='white').pack(anchor=tk.W)
        
        csv_btn_frame = tk.Frame(csv_frame, bg='white')
        csv_btn_frame.pack(fill=tk.X, pady=5)
        
        self.csv_file_var = tk.StringVar()
        self.csv_file_var.set("No file selected")
        csv_label = tk.Label(csv_btn_frame, textvariable=self.csv_file_var, 
                           font=("Arial", 9), bg='white', fg='gray')
        csv_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        csv_btn = tk.Button(csv_btn_frame, text="Browse CSV", command=self.browse_csv,
                           bg='#4CAF50', fg='white', font=("Arial", 10))
        csv_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # JSON Upload
        json_frame = tk.Frame(upload_frame, bg='white')
        json_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(json_frame, text="Upload JSON Slack Data:", font=("Arial", 10), bg='white').pack(anchor=tk.W)
        
        json_btn_frame = tk.Frame(json_frame, bg='white')
        json_btn_frame.pack(fill=tk.X, pady=5)
        
        self.json_file_var = tk.StringVar()
        self.json_file_var.set("No file selected")
        json_label = tk.Label(json_btn_frame, textvariable=self.json_file_var, 
                            font=("Arial", 9), bg='white', fg='gray')
        json_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        json_btn = tk.Button(json_btn_frame, text="Browse JSON", command=self.browse_json,
                            bg='#2196F3', fg='white', font=("Arial", 10))
        json_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Process Button
        process_btn = tk.Button(upload_frame, text="Process Files & Build Knowledge Base", 
                               command=self.process_files, bg='#FF9800', fg='white', 
                               font=("Arial", 12, "bold"), height=2)
        process_btn.pack(pady=20)
        
        # Search Section
        search_frame = tk.LabelFrame(main_frame, text="Search Knowledge Base", 
                                   font=("Arial", 12, "bold"), bg='white')
        search_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Search input
        search_input_frame = tk.Frame(search_frame, bg='white')
        search_input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_input_frame, text="Enter your troubleshooting query:", 
                font=("Arial", 10), bg='white').pack(anchor=tk.W)
        
        search_entry_frame = tk.Frame(search_input_frame, bg='white')
        search_entry_frame.pack(fill=tk.X, pady=5)
        
        self.search_entry = tk.Entry(search_entry_frame, font=("Arial", 11))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind('<Return>', lambda e: self.search())
        
        search_btn = tk.Button(search_entry_frame, text="Search", command=self.search,
                              bg='#9C27B0', fg='white', font=("Arial", 10))
        search_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Results
        results_frame = tk.Frame(search_frame, bg='white')
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        tk.Label(results_frame, text="Search Results:", font=("Arial", 10, "bold"), bg='white').pack(anchor=tk.W)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, 
                                                     font=("Consolas", 10), height=15)
        self.results_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Stats
        self.stats_var = tk.StringVar()
        self.stats_var.set("Knowledge Base: 0 chunks")
        stats_label = tk.Label(main_frame, textvariable=self.stats_var, 
                              font=("Arial", 10), bg='white', fg='green')
        stats_label.pack(pady=10)
    
    def initialize_system(self):
        """Initialize the RAG system"""
        def init_thread():
            try:
                self.status_var.set("Loading configuration...")
                self.root.update()
                
                # Load config
                with open("config.yaml", 'r') as f:
                    config = yaml.safe_load(f)
                
                self.status_var.set("Initializing RAG engine...")
                self.root.update()
                
                # Initialize components
                self.rag_engine = TroubleshootingRAGEngine("config.yaml")
                self.data_ingestors = DataIngestors(config)
                
                # Update stats
                stats = self.rag_engine.get_collection_stats()
                self.stats_var.set(f"Knowledge Base: {stats.get('total_chunks', 0)} chunks")
                
                self.status_var.set("Ready! Upload files to get started.")
                
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
                messagebox.showerror("Initialization Error", str(e))
        
        threading.Thread(target=init_thread, daemon=True).start()
    
    def browse_csv(self):
        """Browse for CSV file"""
        filename = filedialog.askopenfilename(
            title="Select CSV Tickets File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_file_var.set(os.path.basename(filename))
            self.csv_file_path = filename
    
    def browse_json(self):
        """Browse for JSON file"""
        filename = filedialog.askopenfilename(
            title="Select JSON Slack File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.json_file_var.set(os.path.basename(filename))
            self.json_file_path = filename
    
    def process_files(self):
        """Process uploaded files"""
        if not hasattr(self, 'csv_file_path') and not hasattr(self, 'json_file_path'):
            messagebox.showwarning("No Files", "Please select at least one file to process.")
            return
        
        def process_thread():
            try:
                self.status_var.set("Processing files...")
                self.root.update()
                
                # Copy files to exports directory
                os.makedirs("./data/exports", exist_ok=True)
                
                files_processed = []
                
                if hasattr(self, 'csv_file_path'):
                    import shutil
                    dest_csv = "./data/exports/uploaded_tickets.csv"
                    shutil.copy2(self.csv_file_path, dest_csv)
                    files_processed.append("CSV tickets")
                
                if hasattr(self, 'json_file_path'):
                    import shutil
                    dest_json = "./data/exports/uploaded_slack.json"
                    shutil.copy2(self.json_file_path, dest_json)
                    files_processed.append("JSON Slack")
                
                self.status_var.set("Ingesting data...")
                self.root.update()
                
                # Ingest data
                chunks = self.data_ingestors.ingest_all_sources("./data/exports")
                
                if chunks:
                    self.status_var.set("Adding to knowledge base...")
                    self.root.update()
                    
                    self.rag_engine.add_knowledge_chunks(chunks)
                    
                    # Update stats
                    stats = self.rag_engine.get_collection_stats()
                    self.stats_var.set(f"Knowledge Base: {stats.get('total_chunks', 0)} chunks")
                    
                    self.status_var.set(f"Success! Processed {len(chunks)} chunks from {', '.join(files_processed)}")
                    messagebox.showinfo("Success", f"Successfully processed {len(chunks)} knowledge chunks!")
                else:
                    self.status_var.set("No data found in files")
                    messagebox.showwarning("No Data", "No valid data found in the uploaded files.")
                
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
                messagebox.showerror("Processing Error", str(e))
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def search(self):
        """Search the knowledge base"""
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Empty Query", "Please enter a search query.")
            return
        
        def search_thread():
            try:
                self.status_var.set("Searching...")
                self.root.update()
                
                results = self.rag_engine.search_similar(query, n_results=5)
                
                # Display results
                self.results_text.delete(1.0, tk.END)
                
                if results:
                    self.results_text.insert(tk.END, f"Query: {query}\n")
                    self.results_text.insert(tk.END, f"Found {len(results)} results:\n\n")
                    self.results_text.insert(tk.END, "=" * 60 + "\n\n")
                    
                    for i, result in enumerate(results, 1):
                        self.results_text.insert(tk.END, f"RESULT {i}:\n")
                        self.results_text.insert(tk.END, f"Source: {result['metadata'].get('source', 'Unknown')}\n")
                        self.results_text.insert(tk.END, f"Similarity: {1 - result['distance']:.3f}\n")
                        self.results_text.insert(tk.END, f"Content:\n{result['content']}\n")
                        self.results_text.insert(tk.END, "-" * 60 + "\n\n")
                    
                    self.status_var.set(f"Found {len(results)} results")
                else:
                    self.results_text.insert(tk.END, f"No results found for: {query}\n\n")
                    self.results_text.insert(tk.END, "Try:\n")
                    self.results_text.insert(tk.END, "- Different keywords\n")
                    self.results_text.insert(tk.END, "- Upload more data first\n")
                    self.results_text.insert(tk.END, "- Check your file format\n")
                    self.status_var.set("No results found")
                
            except Exception as e:
                self.status_var.set(f"Search error: {str(e)}")
                messagebox.showerror("Search Error", str(e))
        
        threading.Thread(target=search_thread, daemon=True).start()
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = SimpleTroubleshootingGUI()
    app.run()
