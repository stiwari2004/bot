#!/usr/bin/env python3
"""
Comprehensive system testing script for Troubleshooting AI
"""
import requests
import json
import time
import sys
from typing import Dict, Any, List

class SystemTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        self.results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def test_health_check(self) -> bool:
        """Test basic health check"""
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status')}")
                return True
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Error: {str(e)}")
            return False
    
    def test_detailed_health(self) -> bool:
        """Test detailed health check"""
        try:
            response = requests.get(f"{self.api_url}/test/health-detailed")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Detailed Health Check", True, f"Database: {data.get('database')}")
                return True
            else:
                self.log_test("Detailed Health Check", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Detailed Health Check", False, f"Error: {str(e)}")
            return False
    
    def test_create_sample_data(self) -> bool:
        """Test sample data creation"""
        try:
            response = requests.post(f"{self.api_url}/demo/create-sample-data")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Sample Data Creation", True, f"Documents: {data.get('documents_created')}, Chunks: {data.get('total_chunks')}")
                return True
            else:
                self.log_test("Sample Data Creation", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Sample Data Creation", False, f"Error: {str(e)}")
            return False
    
    def test_semantic_search(self) -> bool:
        """Test semantic search functionality"""
        try:
            test_queries = [
                "network connectivity problems",
                "database connection issues", 
                "server performance problems"
            ]
            
            all_passed = True
            for query in test_queries:
                form_data = {"query": query}
                response = requests.post(f"{self.api_url}/demo/search-demo", data=form_data)
                
                if response.status_code == 200:
                    data = response.json()
                    results_count = data.get('results_count', 0)
                    self.log_test(f"Search: '{query}'", True, f"Found {results_count} results")
                else:
                    self.log_test(f"Search: '{query}'", False, f"Status code: {response.status_code}")
                    all_passed = False
            
            return all_passed
        except Exception as e:
            self.log_test("Semantic Search", False, f"Error: {str(e)}")
            return False
    
    def test_runbook_generation(self) -> bool:
        """Test runbook generation"""
        try:
            test_issues = [
                "server is running slow and users are complaining",
                "database connection timeout errors",
                "network connectivity issues in office"
            ]
            
            all_passed = True
            for issue in test_issues:
                response = requests.post(
                    f"{self.api_url}/runbooks/demo/generate",
                    params={"issue_description": issue, "top_k": 5}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    confidence = data.get('confidence', 0)
                    self.log_test(f"Runbook: '{issue[:30]}...'", True, f"Confidence: {confidence:.2f}")
                else:
                    self.log_test(f"Runbook: '{issue[:30]}...'", False, f"Status code: {response.status_code}")
                    all_passed = False
            
            return all_passed
        except Exception as e:
            self.log_test("Runbook Generation", False, f"Error: {str(e)}")
            return False
    
    def test_runbook_listing(self) -> bool:
        """Test runbook listing"""
        try:
            response = requests.get(f"{self.api_url}/runbooks/demo/")
            if response.status_code == 200:
                data = response.json()
                runbook_count = len(data) if isinstance(data, list) else 0
                self.log_test("Runbook Listing", True, f"Found {runbook_count} runbooks")
                return True
            else:
                self.log_test("Runbook Listing", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Runbook Listing", False, f"Error: {str(e)}")
            return False
    
    def test_file_upload(self) -> bool:
        """Test file upload functionality"""
        try:
            # Create a test file
            test_content = """# Test Troubleshooting Guide

## Issue: High CPU Usage
When CPU usage is high, check the following:

1. Check running processes with `top` or `htop`
2. Look for runaway processes
3. Check system logs for errors
4. Consider restarting services

## Resolution Steps
- Kill problematic processes
- Restart affected services
- Monitor system performance
"""
            
            files = {"file": ("test_guide.md", test_content, "text/markdown")}
            data = {"source_type": "doc", "title": "Test Troubleshooting Guide"}
            
            response = requests.post(f"{self.api_url}/demo/upload-demo", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                self.log_test("File Upload", True, f"Document ID: {result.get('document_id')}")
                return True
            else:
                self.log_test("File Upload", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("File Upload", False, f"Error: {str(e)}")
            return False
    
    def test_system_stats(self) -> bool:
        """Test system statistics"""
        try:
            response = requests.get(f"{self.api_url}/demo/stats")
            if response.status_code == 200:
                data = response.json()
                docs = data.get('total_documents', 0)
                chunks = data.get('total_chunks', 0)
                self.log_test("System Stats", True, f"Documents: {docs}, Chunks: {chunks}")
                return True
            else:
                self.log_test("System Stats", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("System Stats", False, f"Error: {str(e)}")
            return False
    
    def test_frontend_accessibility(self) -> bool:
        """Test if frontend is accessible"""
        try:
            response = requests.get("http://localhost:3000")
            if response.status_code == 200:
                self.log_test("Frontend Access", True, "Next.js app is running")
                return True
            else:
                self.log_test("Frontend Access", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Frontend Access", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary"""
        print("🧪 Starting Comprehensive System Testing...\n")
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("Detailed Health", self.test_detailed_health),
            ("Sample Data Creation", self.test_create_sample_data),
            ("Semantic Search", self.test_semantic_search),
            ("Runbook Generation", self.test_runbook_generation),
            ("Runbook Listing", self.test_runbook_listing),
            ("File Upload", self.test_file_upload),
            ("System Stats", self.test_system_stats),
            ("Frontend Access", self.test_frontend_accessibility),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                self.log_test(test_name, False, f"Unexpected error: {str(e)}")
            time.sleep(1)  # Brief pause between tests
        
        # Summary
        print(f"\n📊 Test Summary:")
        print(f"   Passed: {passed}/{total}")
        print(f"   Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 All tests passed! System is fully operational.")
        else:
            print("⚠️  Some tests failed. Please check the issues above.")
        
        return {
            "total_tests": total,
            "passed_tests": passed,
            "success_rate": (passed/total)*100,
            "results": self.results
        }

def main():
    """Main testing function"""
    print("🔧 Troubleshooting AI - System Testing")
    print("=" * 50)
    
    tester = SystemTester()
    results = tester.run_all_tests()
    
    # Save results to file
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: test_results.json")
    
    # Exit with appropriate code
    sys.exit(0 if results["passed_tests"] == results["total_tests"] else 1)

if __name__ == "__main__":
    main()
