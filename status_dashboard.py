#!/usr/bin/env python3
"""
System Status Dashboard for Troubleshooting AI
"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

class StatusDashboard:
    def __init__(self, backend_url: str = "http://localhost:8000", frontend_url: str = "http://localhost:3000"):
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.api_url = f"{backend_url}/api/v1"
        
    def check_backend_health(self) -> Dict[str, Any]:
        """Check backend health status"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                return {"status": "healthy", "response_time": response.elapsed.total_seconds()}
            else:
                return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def check_database_status(self) -> Dict[str, Any]:
        """Check database connectivity and status"""
        try:
            response = requests.get(f"{self.api_url}/test/health-detailed", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "connected",
                    "database": data.get("database", "unknown"),
                    "tables": data.get("tables", "unknown"),
                    "vector_extension": data.get("vector_extension", "unknown")
                }
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def check_frontend_status(self) -> Dict[str, Any]:
        """Check frontend accessibility"""
        try:
            response = requests.get(self.frontend_url, timeout=5)
            if response.status_code == 200:
                return {"status": "accessible", "response_time": response.elapsed.total_seconds()}
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            response = requests.get(f"{self.api_url}/demo/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_runbook_stats(self) -> Dict[str, Any]:
        """Get runbook statistics"""
        try:
            response = requests.get(f"{self.api_url}/runbooks/demo/", timeout=5)
            if response.status_code == 200:
                runbooks = response.json()
                return {
                    "total_runbooks": len(runbooks),
                    "runbooks": runbooks
                }
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def display_dashboard(self):
        """Display the status dashboard"""
        print("🔧 Troubleshooting AI - System Status Dashboard")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Backend Status
        print("🔧 Backend Status:")
        backend_health = self.check_backend_health()
        if backend_health["status"] == "healthy":
            print(f"   ✅ Backend: {backend_health['status']} (Response: {backend_health['response_time']:.3f}s)")
        else:
            print(f"   ❌ Backend: {backend_health['status']} - {backend_health['error']}")
        
        # Database Status
        print("\n🗄️  Database Status:")
        db_status = self.check_database_status()
        if db_status["status"] == "connected":
            print(f"   ✅ Database: {db_status['status']}")
            print(f"   ✅ Tables: {db_status['tables']}")
            print(f"   ✅ Vector Extension: {db_status['vector_extension']}")
        else:
            print(f"   ❌ Database: {db_status['status']} - {db_status['error']}")
        
        # Frontend Status
        print("\n🌐 Frontend Status:")
        frontend_status = self.check_frontend_status()
        if frontend_status["status"] == "accessible":
            print(f"   ✅ Frontend: {frontend_status['status']} (Response: {frontend_status['response_time']:.3f}s)")
        else:
            print(f"   ❌ Frontend: {frontend_status['status']} - {frontend_status['error']}")
        
        # System Statistics
        print("\n📊 System Statistics:")
        stats = self.get_system_stats()
        if "error" not in stats:
            print(f"   📄 Documents: {stats.get('total_documents', 0)}")
            print(f"   📝 Chunks: {stats.get('total_chunks', 0)}")
            print(f"   📚 Source Types: {stats.get('by_source_type', {})}")
        else:
            print(f"   ❌ Error fetching stats: {stats['error']}")
        
        # Runbook Statistics
        print("\n📋 Runbook Statistics:")
        runbook_stats = self.get_runbook_stats()
        if "error" not in runbook_stats:
            print(f"   📖 Total Runbooks: {runbook_stats.get('total_runbooks', 0)}")
            if runbook_stats.get('runbooks'):
                print("   📝 Recent Runbooks:")
                for runbook in runbook_stats['runbooks'][:3]:  # Show last 3
                    title = runbook.get('title', 'Unknown')[:50]
                    confidence = runbook.get('confidence', 0)
                    print(f"      • {title}... (Confidence: {confidence:.2f})")
        else:
            print(f"   ❌ Error fetching runbooks: {runbook_stats['error']}")
        
        # Quick Access Links
        print("\n🔗 Quick Access:")
        print(f"   🌐 Frontend: {self.frontend_url}")
        print(f"   🔧 Backend API: {self.backend_url}")
        print(f"   📚 API Docs: {self.backend_url}/docs")
        print(f"   🧪 Test Interface: {self.backend_url}/test")
        
        print("\n" + "=" * 60)

def main():
    """Main dashboard function"""
    dashboard = StatusDashboard()
    dashboard.display_dashboard()

if __name__ == "__main__":
    main()
