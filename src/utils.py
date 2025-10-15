import os
import json
from typing import Dict, Any, List
import logging

def setup_logging(log_file: str = "troubleshooting_rag.log") -> logging.Logger:
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def create_sample_data():
    """Create sample data for testing"""
    # Create sample ticket data
    sample_tickets = [
        {
            'id': 'TICKET-001',
            'description': 'Users reporting slow login times to the application',
            'resolution': 'Restarted authentication service and cleared cache',
            'category': 'Performance',
            'priority': 'Medium',
            'created_date': '2024-01-15',
            'resolved_date': '2024-01-15'
        },
        {
            'id': 'TICKET-002',
            'description': 'Database connection timeout errors',
            'resolution': 'Increased connection pool size and optimized queries',
            'category': 'Database',
            'priority': 'High',
            'created_date': '2024-01-16',
            'resolved_date': '2024-01-16'
        },
        {
            'id': 'TICKET-003',
            'description': 'Disk space running low on server',
            'resolution': 'Cleaned up log files and increased disk space',
            'category': 'Infrastructure',
            'priority': 'High',
            'created_date': '2024-01-17',
            'resolved_date': '2024-01-17'
        }
    ]
    
    # Create sample Slack data
    sample_slack = {
        '#it-support': [
            {
                'user': 'john.doe',
                'text': 'Having issues with the application login',
                'ts': '1642234567.123456'
            },
            {
                'user': 'jane.smith',
                'text': 'Try restarting the auth service, that usually fixes it',
                'ts': '1642234600.123456'
            },
            {
                'user': 'john.doe',
                'text': 'That worked! Thanks',
                'ts': '1642234700.123456'
            }
        ]
    }
    
    # Create directories
    os.makedirs('./data/exports', exist_ok=True)
    
    # Save sample data
    import pandas as pd
    df = pd.DataFrame(sample_tickets)
    df.to_csv('./data/exports/sample_tickets.csv', index=False)
    
    with open('./data/exports/sample_slack.json', 'w') as f:
        json.dump(sample_slack, f, indent=2)
    
    print("Sample data created in ./data/exports/")
    print("- sample_tickets.csv")
    print("- sample_slack.json")

def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration"""
    required_sections = ['data_sources', 'vector_store', 'processing']
    
    for section in required_sections:
        if section not in config:
            print(f"Missing required config section: {section}")
            return False
    
    return True

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get information about a file"""
    if not os.path.exists(file_path):
        return {'exists': False}
    
    stat = os.stat(file_path)
    return {
        'exists': True,
        'size': stat.st_size,
        'modified': stat.st_mtime,
        'extension': os.path.splitext(file_path)[1].lower()
    }
