import os
import json
import pandas as pd
import glob
from typing import List, Dict, Any
import logging
from datetime import datetime
import re

class DataIngestors:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def ingest_all_sources(self, data_directory: str = "./data/exports") -> List[Dict[str, Any]]:
        """Ingest data from all configured sources"""
        all_chunks = []
        
        # Ingest tickets
        if 'tickets' in self.config['data_sources']['enabled']:
            ticket_chunks = self.ingest_tickets(data_directory)
            all_chunks.extend(ticket_chunks)
        
        # Ingest Slack data
        if 'slack' in self.config['data_sources']['enabled']:
            slack_chunks = self.ingest_slack(data_directory)
            all_chunks.extend(slack_chunks)
        
        # Ingest logs
        if 'logs' in self.config['data_sources']['enabled']:
            log_chunks = self.ingest_logs(data_directory)
            all_chunks.extend(log_chunks)
        
        # Ingest documentation
        if 'documentation' in self.config['data_sources']['enabled']:
            doc_chunks = self.ingest_documentation(data_directory)
            all_chunks.extend(doc_chunks)
        
        self.logger.info(f"Total chunks ingested: {len(all_chunks)}")
        return all_chunks
    
    def ingest_tickets(self, data_directory: str) -> List[Dict[str, Any]]:
        """Ingest ticket data from CSV files"""
        chunks = []
        
        # Find CSV files
        csv_files = []
        for pattern in self.config['data_sources']['tickets']['file_patterns']:
            csv_files.extend(glob.glob(os.path.join(data_directory, pattern)))
        
        self.logger.info(f"Found {len(csv_files)} ticket files")
        
        for file_path in csv_files:
            try:
                df = pd.read_csv(file_path)
                self.logger.info(f"Processing {file_path} with {len(df)} tickets")
                
                for _, ticket in df.iterrows():
                    if self.is_valid_ticket(ticket):
                        chunk = self.process_ticket(ticket, file_path)
                        chunks.append(chunk)
                        
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
        
        return chunks
    
    def is_valid_ticket(self, ticket: pd.Series) -> bool:
        """Check if ticket is valid for processing"""
        required_cols = self.config['data_sources']['tickets']['required_columns']
        return all(col in ticket and pd.notna(ticket[col]) for col in required_cols)
    
    def process_ticket(self, ticket: pd.Series, source_file: str) -> Dict[str, Any]:
        """Process a single ticket into a knowledge chunk"""
        content = f"Issue: {ticket.get('description', '')}\n"
        content += f"Resolution: {ticket.get('resolution', '')}\n"
        content += f"Category: {ticket.get('category', 'Unknown')}\n"
        content += f"Priority: {ticket.get('priority', 'Unknown')}"
        
        return {
            'id': f"ticket_{ticket.get('id', 'unknown')}_{hash(content) % 10000}",
            'content': content,
            'metadata': {
                'source': 'tickets',
                'ticket_id': str(ticket.get('id', '')),
                'category': str(ticket.get('category', '')),
                'priority': str(ticket.get('priority', '')),
                'source_file': source_file,
                'ingestion_date': datetime.now().isoformat()
            }
        }
    
    def ingest_slack(self, data_directory: str) -> List[Dict[str, Any]]:
        """Ingest Slack data from JSON files"""
        chunks = []
        
        # Find JSON files
        json_files = []
        for pattern in self.config['data_sources']['slack']['file_patterns']:
            json_files.extend(glob.glob(os.path.join(data_directory, pattern)))
        
        self.logger.info(f"Found {len(json_files)} Slack files")
        
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    slack_data = json.load(f)
                
                for channel, messages in slack_data.items():
                    if isinstance(messages, list):
                        thread_chunks = self.process_slack_channel(channel, messages, file_path)
                        chunks.extend(thread_chunks)
                        
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
        
        return chunks
    
    def process_slack_channel(self, channel: str, messages: List[Dict], source_file: str) -> List[Dict[str, Any]]:
        """Process messages from a Slack channel"""
        chunks = []
        
        # Group messages into threads
        threads = self.group_messages_into_threads(messages)
        
        for thread in threads:
            if self.is_troubleshooting_thread(thread):
                chunk = self.process_slack_thread(channel, thread, source_file)
                chunks.append(chunk)
        
        return chunks
    
    def group_messages_into_threads(self, messages: List[Dict]) -> List[List[Dict]]:
        """Group messages into conversation threads"""
        threads = []
        current_thread = []
        
        for message in messages:
            if self.is_new_thread(message):
                if current_thread:
                    threads.append(current_thread)
                current_thread = [message]
            else:
                current_thread.append(message)
        
        if current_thread:
            threads.append(current_thread)
        
        return threads
    
    def is_new_thread(self, message: Dict) -> bool:
        """Determine if message starts a new thread"""
        # Simple heuristic: if message is more than 1 hour after previous message
        return True  # Simplified for now
    
    def is_troubleshooting_thread(self, thread: List[Dict]) -> bool:
        """Check if thread contains troubleshooting content"""
        troubleshooting_keywords = [
            'error', 'issue', 'problem', 'down', 'slow', 'broken',
            'fix', 'resolve', 'solution', 'troubleshoot', 'debug',
            'not working', 'failed', 'crash', 'timeout'
        ]
        
        thread_text = ' '.join([msg.get('text', '') for msg in thread]).lower()
        return any(keyword in thread_text for keyword in troubleshooting_keywords)
    
    def process_slack_thread(self, channel: str, thread: List[Dict], source_file: str) -> Dict[str, Any]:
        """Process a Slack thread into a knowledge chunk"""
        content = f"Channel: {channel}\n"
        content += f"Participants: {', '.join(set(msg.get('user', 'unknown') for msg in thread))}\n\n"
        
        for msg in thread:
            content += f"{msg.get('user', 'unknown')}: {msg.get('text', '')}\n"
        
        return {
            'id': f"slack_{channel}_{hash(content) % 10000}",
            'content': content,
            'metadata': {
                'source': 'slack',
                'channel': channel,
                'participants': ', '.join(set(msg.get('user', 'unknown') for msg in thread)),
                'message_count': len(thread),
                'source_file': source_file,
                'ingestion_date': datetime.now().isoformat()
            }
        }
    
    def ingest_logs(self, data_directory: str) -> List[Dict[str, Any]]:
        """Ingest log files"""
        chunks = []
        
        # Find log files
        log_files = []
        for pattern in self.config['data_sources']['logs']['file_patterns']:
            log_files.extend(glob.glob(os.path.join(data_directory, pattern)))
        
        self.logger.info(f"Found {len(log_files)} log files")
        
        for file_path in log_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Extract error patterns
                error_chunks = self.extract_error_patterns(content, file_path)
                chunks.extend(error_chunks)
                
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
        
        return chunks
    
    def extract_error_patterns(self, content: str, source_file: str) -> List[Dict[str, Any]]:
        """Extract error patterns from log content"""
        chunks = []
        error_patterns = self.config['data_sources']['logs']['error_patterns']
        
        lines = content.split('\n')
        current_error = []
        
        for line in lines:
            if any(pattern in line for pattern in error_patterns):
                if current_error:
                    # Process accumulated error
                    chunk = self.process_error_chunk(current_error, source_file)
                    chunks.append(chunk)
                    current_error = []
                current_error.append(line)
            elif current_error and len(current_error) < 10:  # Limit error context
                current_error.append(line)
        
        # Process final error if exists
        if current_error:
            chunk = self.process_error_chunk(current_error, source_file)
            chunks.append(chunk)
        
        return chunks
    
    def process_error_chunk(self, error_lines: List[str], source_file: str) -> Dict[str, Any]:
        """Process error lines into a knowledge chunk"""
        content = '\n'.join(error_lines)
        
        return {
            'id': f"log_{hash(content) % 10000}",
            'content': content,
            'metadata': {
                'source': 'logs',
                'error_type': self.classify_error_type(error_lines),
                'source_file': source_file,
                'line_count': len(error_lines),
                'ingestion_date': datetime.now().isoformat()
            }
        }
    
    def classify_error_type(self, error_lines: List[str]) -> str:
        """Classify the type of error"""
        error_text = ' '.join(error_lines).lower()
        
        if 'connection' in error_text or 'network' in error_text:
            return 'network'
        elif 'database' in error_text or 'sql' in error_text:
            return 'database'
        elif 'memory' in error_text or 'oom' in error_text:
            return 'memory'
        elif 'disk' in error_text or 'space' in error_text:
            return 'disk'
        else:
            return 'general'
    
    def ingest_documentation(self, data_directory: str) -> List[Dict[str, Any]]:
        """Ingest documentation files"""
        chunks = []
        
        # Find documentation files
        doc_files = []
        for pattern in self.config['data_sources']['documentation']['file_patterns']:
            doc_files.extend(glob.glob(os.path.join(data_directory, pattern)))
        
        self.logger.info(f"Found {len(doc_files)} documentation files")
        
        for file_path in doc_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Split into chunks
                doc_chunks = self.chunk_documentation(content, file_path)
                chunks.extend(doc_chunks)
                
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
        
        return chunks
    
    def chunk_documentation(self, content: str, source_file: str) -> List[Dict[str, Any]]:
        """Split documentation into chunks"""
        chunks = []
        chunk_size = self.config['processing']['chunk_size']
        
        # Simple chunking by paragraphs
        paragraphs = content.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) < chunk_size:
                current_chunk += paragraph + '\n\n'
            else:
                if current_chunk.strip():
                    chunk = {
                        'id': f"doc_{hash(current_chunk) % 10000}",
                        'content': current_chunk.strip(),
                        'metadata': {
                            'source': 'documentation',
                            'source_file': source_file,
                            'ingestion_date': datetime.now().isoformat()
                        }
                    }
                    chunks.append(chunk)
                current_chunk = paragraph + '\n\n'
        
        # Add final chunk
        if current_chunk.strip():
            chunk = {
                'id': f"doc_{hash(current_chunk) % 10000}",
                'content': current_chunk.strip(),
                'metadata': {
                    'source': 'documentation',
                    'source_file': source_file,
                    'ingestion_date': datetime.now().isoformat()
                }
            }
            chunks.append(chunk)
        
        return chunks
