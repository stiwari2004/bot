"""
Database connector for PostgreSQL, MySQL, etc. (MF-4: Command injection protection)
"""
import json
from typing import Any, Dict
from app.core.logging import get_logger
from app.services.infrastructure.base_connector import InfrastructureConnector
from app.services.infrastructure.command_validator import CommandValidator

logger = get_logger(__name__)


class DatabaseConnector(InfrastructureConnector):
    """Database connector for PostgreSQL, MySQL, etc."""
    
    async def execute_command(self, command: str, connection_config: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Execute SQL query
        
        connection_config:
        {
            "host": "db.example.com",
            "port": 5432,
            "database": "mydb",
            "username": "user",
            "password": "password",
            "db_type": "postgresql" | "mysql" | "mssql"
        }
        """
        try:
            # Validate command to prevent SQL injection (MF-4)
            is_safe, error_msg = CommandValidator.validate_command(command, "sql")
            if not is_safe:
                logger.error(f"Command injection attempt blocked: {error_msg}")
                return {
                    "success": False,
                    "output": "",
                    "error": f"Command validation failed: {error_msg}",
                    "exit_code": -1
                }
            
            db_type = connection_config.get("db_type", "postgresql")
            host = connection_config.get("host")
            port = connection_config.get("port", 5432)
            database = connection_config.get("database")
            username = connection_config.get("username")
            password = connection_config.get("password")
            
            if db_type == "postgresql":
                import asyncpg
                conn = await asyncpg.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    timeout=timeout
                )
                try:
                    result = await conn.fetch(command)
                    return {
                        "success": True,
                        "output": json.dumps([dict(row) for row in result], default=str),
                        "error": "",
                        "exit_code": 0
                    }
                finally:
                    await conn.close()
            
            elif db_type == "mysql":
                import aiomysql
                conn = await aiomysql.connect(
                    host=host,
                    port=port,
                    db=database,
                    user=username,
                    password=password,
                    connect_timeout=timeout
                )
                try:
                    cursor = await conn.cursor()
                    await cursor.execute(command)
                    result = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    await cursor.close()
                    
                    return {
                        "success": True,
                        "output": json.dumps([dict(zip(columns, row)) for row in result], default=str),
                        "error": "",
                        "exit_code": 0
                    }
                finally:
                    conn.close()
            
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Unsupported database type: {db_type}",
                    "exit_code": -1
                }
                
        except Exception as e:
            logger.error(f"Database execution error: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }




