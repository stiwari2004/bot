import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
from typing import Optional
import logging

class TroubleshootingRAGGUI:
    def __init__(self, rag_engine, data_ingestors):
        self.rag_engine = rag_engine
        self.data_ingestors = data_ingestors
        self.logger = logging.getLogger(__name__)
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Troubleshooting RAG System")
        self.root.geometry("1200x800")
        
        # Setup GUI
        self.setup_gui()
        self.update_status("Ready")
        
        # Load initial stats
        self.update_stats()
    
    def setup_gui(self):
        """Setup the GUI components"""
        # Configure root window
        self.root.configure(bg='white')
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Troubleshooting RAG System", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Create content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Left panel - Controls
        self.setup_control_panel(content_frame)
        
        # Right panel - Query and Results
        self.setup_query_panel(content_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_control_panel(self, parent):
        """Setup the control panel"""
        control_frame = ttk.LabelFrame(parent, text="Data Management", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Data ingestion section
        ttk.Label(control_frame, text="Data Ingestion", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        
        ttk.Button(control_frame, text="Select Data Directory", 
                  command=self.select_data_directory).grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)
        
        ttk.Button(control_frame, text="Ingest All Data", 
                  command=self.ingest_all_data).grid(row=2, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)
        
        # Knowledge base management
        ttk.Label(control_frame, text="Knowledge Base", font=("Arial", 12, "bold")).grid(
            row=3, column=0, columnspan=2, pady=(20, 10), sticky=tk.W)
        
        ttk.Button(control_frame, text="Refresh Stats", 
                  command=self.update_stats).grid(row=4, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)
        
        ttk.Button(control_frame, text="Clear Knowledge Base", 
                  command=self.clear_knowledge_base).grid(row=5, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E)
        
        # Stats display
        self.stats_frame = ttk.LabelFrame(control_frame, text="Statistics", padding="5")
        self.stats_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0), sticky=tk.W+tk.E)
        
        self.stats_label = ttk.Label(self.stats_frame, text="Loading...")
        self.stats_label.grid(row=0, column=0, sticky=tk.W)
    
    def setup_query_panel(self, parent):
        """Setup the query panel"""
        query_frame = ttk.Frame(parent)
        query_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        query_frame.columnconfigure(0, weight=1)
        query_frame.rowconfigure(1, weight=1)
        
        # Query input section
        query_input_frame = ttk.LabelFrame(query_frame, text="Query", padding="10")
        query_input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        query_input_frame.columnconfigure(0, weight=1)
        
        self.query_entry = ttk.Entry(query_input_frame, font=("Arial", 11))
        self.query_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        self.query_entry.bind('<Return>', lambda e: self.search())
        
        ttk.Button(query_input_frame, text="Search", 
                  command=self.search).grid(row=0, column=1)
        
        # Results section
        results_frame = ttk.LabelFrame(query_frame, text="Search Results", padding="10")
        results_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Create notebook for results
        self.results_notebook = ttk.Notebook(results_frame)
        self.results_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Results tab
        self.results_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.results_frame, text="Results")
        
        self.results_text = scrolledtext.ScrolledText(
            self.results_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        
        # Logs tab
        self.logs_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.logs_frame, text="Logs")
        
        self.logs_text = scrolledtext.ScrolledText(
            self.logs_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.logs_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.logs_frame.columnconfigure(0, weight=1)
        self.logs_frame.rowconfigure(0, weight=1)
    
    def setup_status_bar(self, parent):
        """Setup the status bar"""
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        
        status_bar = ttk.Label(parent, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    
    def update_status(self, message: str):
        """Update status bar"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def update_stats(self):
        """Update statistics display"""
        try:
            stats = self.rag_engine.get_collection_stats()
            stats_text = f"Total Knowledge Chunks: {stats.get('total_chunks', 0)}\n"
            stats_text += f"Collection: {stats.get('collection_name', 'N/A')}\n"
            stats_text += f"Model: {stats.get('embedding_model', 'N/A')}"
            
            self.stats_label.config(text=stats_text)
        except Exception as e:
            self.stats_label.config(text=f"Error loading stats: {e}")
    
    def select_data_directory(self):
        """Select data directory for ingestion"""
        directory = filedialog.askdirectory(title="Select Data Directory")
        if directory:
            self.data_directory = directory
            self.update_status(f"Selected directory: {directory}")
    
    def ingest_all_data(self):
        """Ingest all data in a separate thread"""
        if not hasattr(self, 'data_directory'):
            messagebox.showwarning("Warning", "Please select a data directory first")
            return
        
        def ingest_thread():
            try:
                self.update_status("Ingesting data...")
                self.log_message("Starting data ingestion...")
                
                chunks = self.data_ingestors.ingest_all_sources(self.data_directory)
                
                if chunks:
                    self.rag_engine.add_knowledge_chunks(chunks)
                    self.log_message(f"Successfully ingested {len(chunks)} knowledge chunks")
                    self.update_status(f"Ingestion complete: {len(chunks)} chunks added")
                else:
                    self.log_message("No data found to ingest")
                    self.update_status("No data found to ingest")
                
                self.update_stats()
                
            except Exception as e:
                error_msg = f"Error during ingestion: {e}"
                self.log_message(error_msg)
                self.update_status("Ingestion failed")
                messagebox.showerror("Error", error_msg)
        
        # Run in separate thread to avoid blocking GUI
        threading.Thread(target=ingest_thread, daemon=True).start()
    
    def search(self):
        """Perform search in a separate thread"""
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search query")
            return
        
        def search_thread():
            try:
                self.update_status("Searching...")
                self.log_message(f"Searching for: {query}")
                
                results = self.rag_engine.search_similar(query, n_results=5)
                
                # Display results
                self.display_results(results, query)
                
                self.update_status(f"Found {len(results)} results")
                self.log_message(f"Search completed: {len(results)} results found")
                
            except Exception as e:
                error_msg = f"Error during search: {e}"
                self.log_message(error_msg)
                self.update_status("Search failed")
                messagebox.showerror("Error", error_msg)
        
        # Run in separate thread to avoid blocking GUI
        threading.Thread(target=search_thread, daemon=True).start()
    
    def display_results(self, results: list, query: str):
        """Display search results"""
        self.results_text.delete(1.0, tk.END)
        
        if not results:
            self.results_text.insert(tk.END, "No results found.")
            return
        
        # Display results
        self.results_text.insert(tk.END, f"Query: {query}\n")
        self.results_text.insert(tk.END, f"Found {len(results)} results:\n\n")
        self.results_text.insert(tk.END, "=" * 80 + "\n\n")
        
        for i, result in enumerate(results, 1):
            self.results_text.insert(tk.END, f"Result {i}:\n")
            self.results_text.insert(tk.END, f"Source: {result['metadata'].get('source', 'Unknown')}\n")
            self.results_text.insert(tk.END, f"Distance: {result['distance']:.4f}\n")
            self.results_text.insert(tk.END, f"Content:\n{result['content']}\n")
            self.results_text.insert(tk.END, "-" * 80 + "\n\n")
    
    def clear_knowledge_base(self):
        """Clear the knowledge base"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the knowledge base?"):
            try:
                self.rag_engine.clear_knowledge_base()
                self.update_stats()
                self.update_status("Knowledge base cleared")
                self.log_message("Knowledge base cleared successfully")
                messagebox.showinfo("Success", "Knowledge base cleared successfully")
            except Exception as e:
                error_msg = f"Error clearing knowledge base: {e}"
                self.log_message(error_msg)
                messagebox.showerror("Error", error_msg)
    
    def log_message(self, message: str):
        """Add message to log display"""
        self.logs_text.insert(tk.END, f"{message}\n")
        self.logs_text.see(tk.END)
        self.root.update_idletasks()
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()
