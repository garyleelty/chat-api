#!/usr/bin/env python3
"""
Basic API Functionality Tests for Doubao Chat API

This module contains comprehensive tests to verify the basic API functionality
including health checks, chat endpoints, and conversation management.
"""

import asyncio
import httpx
import logging
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APITester:
    """Test suite for basic API functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.test_results: list = []
        self.client = None
        
    async def setup(self):
        """Setup test client."""
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def teardown(self):
        """Cleanup test client."""
        if self.client:
            await self.client.aclose()
    
    async def run_all_tests(self) -> bool:
        """Run all API functionality tests."""
        logger.info("Starting API functionality tests...")
        
        await self.setup()
        
        try:
            # Test basic connectivity
            await self.test_server_connectivity()
            
            # Test root endpoint
            await self.test_root_endpoint()
            
            # Test health check endpoint
            await self.test_health_check()
            
            # Test chat endpoint (basic functionality)
            await self.test_chat_endpoint()
            
            # Test conversation history
            await self.test_conversation_history()
            
            # Test clear conversation
            await self.test_clear_conversation()
            
            # Test request validation
            await self.test_request_validation()
            
            # Test response format
            await self.test_response_format()
            
            # Generate summary
            return self.generate_summary()
            
        finally:
            await self.teardown()
    
    async def test_server_connectivity(self):
        """Test basic server connectivity."""
        test_name = "Server Connectivity"
        
        try:
            # Test if server is reachable
            response = await self.client.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                self._record_test_result(test_name, True, "Server is reachable and responding")
            else:
                self._record_test_result(test_name, False, f"Server returned status code: {response.status_code}")
                
        except httpx.ConnectError:
            self._record_test_result(test_name, False, "Failed to connect to server")
        except Exception as e:
            self._record_test_result(test_name, False, f"Connectivity test failed: {str(e)}")
    
    async def test_root_endpoint(self):
        """Test root endpoint functionality."""
        test_name = "Root Endpoint"
        
        try:
            response = await self.client.get(f"{self.base_url}/")
            
            if response.status_code != 200:
                self._record_test_result(test_name, False, f"Root endpoint returned {response.status_code}")
                return
            
            data = response.json()
            
            # Validate response structure
            required_fields = ['status', 'initialized', 'doubao_url', 'success']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Missing fields in response: {missing_fields}")
                return
            
            # Validate field types
            if not isinstance(data['initialized'], bool):
                self._record_test_result(test_name, False, "'initialized' field should be boolean")
                return
                
            if not isinstance(data['success'], bool):
                self._record_test_result(test_name, False, "'success' field should be boolean")
                return
            
            # Check metadata if present
            if 'metadata' in data:
                metadata = data['metadata']
                if 'timestamp' not in metadata or 'response_time_ms' not in metadata:
                    logger.warning("Metadata missing timestamp or response_time_ms")
            
            self._record_test_result(test_name, True, f"Root endpoint working correctly - initialized: {data['initialized']}")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Root endpoint test failed: {str(e)}")
    
    async def test_health_check(self):
        """Test health check endpoint."""
        test_name = "Health Check Endpoint"
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            
            if response.status_code != 200:
                self._record_test_result(test_name, False, f"Health check returned {response.status_code}")
                return
            
            data = response.json()
            
            # Validate health check response structure
            required_fields = ['healthy', 'status', 'initialized']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Health check missing fields: {missing_fields}")
                return
            
            # Check if health check provides detailed information
            detailed_fields = ['session_age', 'last_activity', 'browser_connected', 'page_ready']
            has_detailed_info = any(field in data for field in detailed_fields)
            
            if has_detailed_info:
                logger.info(f"Health check provides detailed status: healthy={data['healthy']}, initialized={data['initialized']}")
            
            self._record_test_result(test_name, True, f"Health check working - healthy: {data['healthy']}")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Health check test failed: {str(e)}")
    
    async def test_chat_endpoint(self):
        """Test chat endpoint basic functionality."""
        test_name = "Chat Endpoint"
        
        try:
            # Test with a simple message
            test_message = "Hello, this is a test message"
            payload = {
                "message": test_message,
                "clear_history": False
            }
            
            start_time = time.time()
            response = await self.client.post(f"{self.base_url}/chat", json=payload)
            response_time = time.time() - start_time
            
            if response.status_code != 200:
                self._record_test_result(test_name, False, f"Chat endpoint returned {response.status_code}: {response.text}")
                return
            
            data = response.json()
            
            # Validate chat response structure
            required_fields = ['response', 'success', 'metadata']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Chat response missing fields: {missing_fields}")
                return
            
            # Check response content
            if data['success']:
                if data['response'] and len(data['response']) > 0:
                    self._record_test_result(test_name, True, 
                        f"Chat endpoint working - got response of {len(data['response'])} chars in {response_time:.2f}s")
                else:
                    self._record_test_result(test_name, False, "Chat endpoint returned success but empty response")
            else:
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                self._record_test_result(test_name, False, f"Chat endpoint returned error: {error_msg}")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Chat endpoint test failed: {str(e)}")
    
    async def test_conversation_history(self):
        """Test conversation history endpoint."""
        test_name = "Conversation History"
        
        try:
            response = await self.client.get(f"{self.base_url}/history")
            
            if response.status_code != 200:
                self._record_test_result(test_name, False, f"History endpoint returned {response.status_code}")
                return
            
            data = response.json()
            
            # Validate history response structure
            required_fields = ['messages', 'success', 'metadata']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self._record_test_result(test_name, False, f"History response missing fields: {missing_fields}")
                return
            
            # Check messages field
            if not isinstance(data['messages'], list):
                self._record_test_result(test_name, False, "'messages' field should be a list")
                return
            
            self._record_test_result(test_name, True, f"History endpoint working - {len(data['messages'])} messages retrieved")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"History endpoint test failed: {str(e)}")
    
    async def test_clear_conversation(self):
        """Test clear conversation functionality."""
        test_name = "Clear Conversation"
        
        try:
            response = await self.client.post(f"{self.base_url}/clear")
            
            if response.status_code != 200:
                self._record_test_result(test_name, False, f"Clear conversation returned {response.status_code}")
                return
            
            data = response.json()
            
            # Validate clear response structure
            required_fields = ['success', 'message', 'metadata']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Clear response missing fields: {missing_fields}")
                return
            
            if data['success']:
                self._record_test_result(test_name, True, "Clear conversation working correctly")
            else:
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                self._record_test_result(test_name, False, f"Clear conversation failed: {error_msg}")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Clear conversation test failed: {str(e)}")
    
    async def test_request_validation(self):
        """Test request validation and error handling."""
        test_name = "Request Validation"
        
        validation_tests = [
            # Test empty message
            {
                "payload": {"message": "", "clear_history": False},
                "expected_status": 422,
                "description": "empty message"
            },
            # Test message too short
            {
                "payload": {"message": "a", "clear_history": False},
                "expected_status": 422,
                "description": "message too short"
            },
            # Test message too long (assuming 4000 char limit)
            {
                "payload": {"message": "x" * 5000, "clear_history": False},
                "expected_status": 422,
                "description": "message too long"
            },
            # Test missing message field
            {
                "payload": {"clear_history": False},
                "expected_status": 422,
                "description": "missing message field"
            }
        ]
        
        passed_validations = 0
        failed_validations = []
        
        for test_case in validation_tests:
            try:
                response = await self.client.post(f"{self.base_url}/chat", json=test_case["payload"])
                
                if response.status_code == test_case["expected_status"]:
                    passed_validations += 1
                    logger.info(f"✓ Validation test passed: {test_case['description']}")
                else:
                    failed_validations.append(f"{test_case['description']}: expected {test_case['expected_status']}, got {response.status_code}")
                    
            except Exception as e:
                failed_validations.append(f"{test_case['description']}: {str(e)}")
        
        if failed_validations:
            self._record_test_result(test_name, False, f"Validation failures: {'; '.join(failed_validations)}")
        else:
            self._record_test_result(test_name, True, f"All {passed_validations} validation tests passed")
    
    async def test_response_format(self):
        """Test response format consistency."""
        test_name = "Response Format"
        
        try:
            # Test chat response format
            payload = {"message": "Test message for format validation", "clear_history": False}
            response = await self.client.post(f"{self.base_url}/chat", json=payload)
            
            if response.status_code != 200:
                self._record_test_result(test_name, False, "Cannot test format - chat endpoint failed")
                return
            
            data = response.json()
            
            # Check metadata structure
            if 'metadata' not in data:
                self._record_test_result(test_name, False, "Response missing metadata")
                return
            
            metadata = data['metadata']
            required_metadata = ['timestamp', 'response_time_ms', 'api_version']
            missing_metadata = [field for field in required_metadata if field not in metadata]
            
            if missing_metadata:
                self._record_test_result(test_name, False, f"Metadata missing fields: {missing_metadata}")
                return
            
            # Validate timestamp format
            try:
                datetime.fromisoformat(metadata['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                self._record_test_result(test_name, False, "Invalid timestamp format in metadata")
                return
            
            # Validate response_time_ms is numeric
            if not isinstance(metadata['response_time_ms'], (int, float)):
                self._record_test_result(test_name, False, "response_time_ms should be numeric")
                return
            
            self._record_test_result(test_name, True, "Response format is consistent and valid")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Response format test failed: {str(e)}")
    
    def _record_test_result(self, test_name: str, passed: bool, message: str):
        """Record a test result."""
        result = {
            'test_name': test_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{status}: {test_name} - {message}")
    
    def generate_summary(self) -> bool:
        """Generate test summary and return overall success status."""
        logger.info("\n" + "="*60)
        logger.info("API FUNCTIONALITY TEST SUMMARY")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        
        if failed_tests > 0:
            logger.info("\nFAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    logger.info(f"  ✗ {result['test_name']}: {result['message']}")
        
        logger.info("\nPASSED TESTS:")
        for result in self.test_results:
            if result['passed']:
                logger.info(f"  ✓ {result['test_name']}: {result['message']}")
        
        overall_success = failed_tests == 0
        status = "SUCCESS" if overall_success else "FAILURE"
        logger.info(f"\nOVERALL STATUS: {status}")
        
        return overall_success


async def main():
    """Main test runner."""
    # Allow base URL to be configured via environment variable
    import os
    base_url = os.environ.get('API_BASE_URL', 'http://localhost:8000')
    
    tester = APITester(base_url)
    success = await tester.run_all_tests()
    
    if success:
        logger.info("\n🎉 All API functionality tests passed!")
        logger.info("The Doubao Chat API is functioning correctly.")
    else:
        logger.error("\n❌ Some API functionality tests failed!")
        logger.error("Please check the API implementation and configuration.")
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)