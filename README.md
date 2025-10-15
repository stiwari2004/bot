# Troubleshooting RAG System

A Python-based RAG (Retrieval-Augmented Generation) system for IT troubleshooting that learns from tickets, Slack conversations, logs, and documentation.

## Features

- **Multi-source data ingestion**: CSV tickets, JSON Slack exports, log files, documentation
- **Vector-based semantic search**: Find similar troubleshooting cases using AI embeddings
- **User-friendly GUI**: Easy-to-use interface for data management and querying
- **Real-time processing**: Threaded operations that don't freeze the interface
- **Knowledge base management**: Clear, refresh, and monitor your troubleshooting knowledge

## Quick Start

### 1. Installation

```bash
# Navigate to the project directory
cd ~/Documents/troubleshooting_rag

# Install dependencies
python3 install.py
```

### 2. Create Sample Data (Optional)

```bash
python3 main.py --create-sample
```

### 3. Run the Application

```bash
python3 run.py
```

## How to Use

### Data Ingestion

1. **Prepare your data files**:
   - **Tickets**: Export as CSV with columns: `id`, `description`, `resolution`, `category`, `priority`
   - **Slack**: Export as JSON with channel conversations
   - **Logs**: Place `.log` or `.txt` files in your data directory
   - **Documentation**: Place `.md`, `.txt`, or `.docx` files in your data directory

2. **In the GUI**:
   - Click "Select Data Directory" and choose the folder containing your data files
   - Click "Ingest All Data" to process and add to the knowledge base
   - View statistics to see how many knowledge chunks were created

### Searching

1. **Enter your query** in the search box (e.g., "users can't login", "database timeout errors")
2. **Click Search** to find similar troubleshooting cases
3. **Review results** showing:
   - Source of the information (tickets, Slack, logs, docs)
   - Similarity score (lower is more similar)
   - Full content of matching cases

### Knowledge Base Management

- **Refresh Stats**: Update the display with current knowledge base statistics
- **Clear Knowledge Base**: Remove all stored knowledge (use with caution)
- **Logs Tab**: View real-time processing logs and system messages

## File Structure

```
troubleshooting_rag/
├── requirements.txt          # Dependencies
├── config.yaml              # Configuration
├── main.py                  # Main application
├── run.py                   # Simple runner
├── install.py               # Installation script
├── src/
│   ├── rag_engine.py        # Core RAG functionality
│   ├── data_ingestors.py    # Data processing
│   ├── gui.py              # GUI interface
│   └── utils.py            # Utilities
└── data/
    ├── exports/            # Your data files go here
    ├── vector_db/          # Vector database storage
    └── logs/               # Application logs
```

## Configuration

Edit `config.yaml` to customize:

- **Data sources**: Enable/disable different data types
- **File patterns**: Specify which file types to process
- **Processing settings**: Chunk size, overlap, batch size
- **Vector store**: Database location and embedding model
- **GUI settings**: Window size, fonts, themes

## Troubleshooting

### Common Issues

1. **Import errors**: Run `python3 install.py` to reinstall dependencies
2. **No results found**: Make sure you've ingested data first
3. **GUI not responding**: Check the Logs tab for error messages
4. **Slow performance**: Reduce chunk size in config.yaml

### Dependencies

- Python 3.7+
- sentence-transformers (for embeddings)
- chromadb (for vector storage)
- pandas (for data processing)
- tkinter (GUI - included with Python)

## Next Steps

This is the foundation for your troubleshooting RAG system. Future enhancements could include:

- **Visual agent**: Screen reading and interaction capabilities
- **Real-time APIs**: Direct integration with ticketing systems
- **Advanced analytics**: Pattern recognition and trend analysis
- **Automation**: Automated resolution suggestions and execution

## Support

Check the Logs tab in the GUI for detailed error messages and system information.

