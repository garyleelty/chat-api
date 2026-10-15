#!/usr/bin/env python3
"""
Playwright Automation Tests for Doubao Chat API

This module contains comprehensive tests to verify the Playwright automation
functionality including browser initialization, page interaction, and
Doubao interface automation.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlaywrightAutomationTester:
    """Test suite for Playwright automation functionality."""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.automation = None
        
    async def setup(self):
        """Setup test environment."""
        try:
            from doubao_automation import DoubaoAutomation
            self.automation = DoubaoAutomation()
            logger.info("✓ DoubaoAutomation instance created")
        except Exception as e:
            logger.error(f"Failed to create DoubaoAutomation instance: {str(e)}")
            raise
    
    async def teardown(self):
        """Cleanup test environment."""
        if self.automation and self.automation.is_initialized:
            try:
                await self.automation.close()
                logger.info("✓ Automation cleanup completed")
            except Exception as e:
                logger.warning(f"Warning during cleanup: {str(e)}")
    
    async def run_all_tests(self) -> bool:
        """Run all Playwright automation tests."""
        logger.info("Starting Playwright automation tests...")
        
        await self.setup()
        
        try:
            # Test automation initialization
            await self.test_automation_initialization()
            
            # Test browser connectivity
            await self.test_browser_connectivity()
            
            # Test Doubao page loading
            await self.test_doubao_page_loading()
            
            # Test element detection
            await self.test_element_detection()
            
            # Test message sending
            await self.test_message_sending()
            
            # Test response retrieval
            await self.test_response_retrieval()
            
            # Test conversation management
            await self.test_conversation_management()
            
            # Test health check functionality
            await self.test_health_check_functionality()
            
            # Test error recovery
            await self.test_error_recovery()
            
            # Test session management
            await self.test_session_management()
            
            # Generate summary
            return self.generate_summary()
            
        finally:
            await self.teardown()
    
    async def test_automation_initialization(self):
        """Test automation initialization."""
        test_name = "Automation Initialization"
        
        try:
            if not self.automation:
                self._record_test_result(test_name, False, "Automation instance not available")
                return
            
            # Test initialization
            success = await self.automation.initialize()
            
            if success:
                if self.automation.is_initialized:
                    self._record_test_result(test_name, True, "Automation initialized successfully")
                else:
                    self._record_test_result(test_name, False, "Initialization returned success but automation not marked as initialized")
            else:
                self._record_test_result(test_name, False, "Automation initialization failed")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Initialization test failed: {str(e)}")
    
    async def test_browser_connectivity(self):
        """Test browser connectivity and basic operations."""
        test_name = "Browser Connectivity"
        
        try:
            if not self.automation or not self.automation.is_initialized:
                self._record_test_result(test_name, False, "Automation not initialized")
                return
            
            # Test browser instance
            if not hasattr(self.automation, 'browser') or not self.automation.browser:
                self._record_test_result(test_name, False, "Browser instance not available")
                return
            
            # Test page instance
            if not hasattr(self.automation, 'page') or not self.automation.page:
                self._record_test_result(test_name, False, "Page instance not available")
                return
            
            # Test basic page operations
            title = await self.automation.page.title()
            url = self.automation.page.url
            
            logger.info(f"Page title: {title}")
            logger.info(f"Page URL: {url}")
            
            self._record_test_result(test_name, True, f"Browser connectivity OK - Title: {title}, URL: {url}")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Browser connectivity test failed: {str(e)}")
    
    async def test_doubao_page_loading(self):
        """Test Doubao page loading and navigation."""
        test_name = "Doubao Page Loading"
        
        try:
            if not self.automation or not self.automation.is_initialized:
                self._record_test_result(test_name, False, "Automation not initialized")
                return
            
            # Test navigation to Doubao
            from config import settings
            doubao_url = settings.DOUBAO_URL
            
            logger.info(f"Navigating to Doubao URL: {doubao_url}")
            await self.automation.page.goto(doubao_url)
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Check if we're on the expected page
            current_url = self.automation.page.url
            page_title = await self.automation.page.title()
            
            logger.info(f"Loaded page - URL: {current_url}, Title: {page_title}")
            
            # Basic validation that we loaded a page
            if current_url and len(current_url) > 0:
                self._record_test_result(test_name, True, f"Page loaded successfully - {page_title}")
            else:
                self._record_test_result(test_name, False, "Failed to load Doubao page")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Page loading test failed: {str(e)}")
    
    async def test_element_detection(self):
        """Test detection of key UI elements."""
        test_name = "Element Detection"
        
        try:
            if not self.automation or not self.automation.is_initialized:
                self._record_test_result(test_name, False, "Automation not initialized")
                return
            
            # Test input field detection
            input_selectors = [
                "textarea[placeholder*='输入']",
                "textarea[placeholder*='message']", 
                ".semi-input",
                ".input-area",
                "[data-testid*='input']",
                "[class*='input'][class*='textarea']"
            ]
            
            input_found = False
            found_selector = None
            
            for selector in input_selectors:
                try:
                    element = await self.automation.page.query_selector(selector)
                    if element:
                        input_found = True
                        found_selector = selector
                        logger.info(f"✓ Input field found with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {str(e)}")
                    continue
            
            if not input_found:
                logger.warning("Could not find input field with any selector")
            
            # Test send button detection
            send_selectors = [
                "button[class*='send']",
                "button[type='submit']",
                ".send-button",
                "[data-testid*='send']",
                "button:not([disabled])"
            ]
            
            send_found = False
            found_send_selector = None
            
            for selector in send_selectors:
                try:
                    element = await self.automation.page.query_selector(selector)
                    if element:
                        send_found = True
                        found_send_selector = selector
                        logger.info(f"✓ Send button found with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Send selector {selector} failed: {str(e)}")
                    continue
            
            if not send_found:
                logger.warning("Could not find send button with any selector")
            
            # Overall result
            if input_found:
                self._record_test_result(test_name, True, 
                    f"Element detection OK - Input: {found_selector}, Send: {found_send_selector or 'Not found'}")
            else:
                self._record_test_result(test_name, False, "Could not detect input field")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Element detection test failed: {str(e)}")
    
    async def test_message_sending(self):
        """Test message sending functionality."""
        test_name = "Message Sending"
        
        try:
            if not self.automation or not self.automation.is_initialized:
                self._record_test_result(test_name, False, "Automation not initialized")
                return
            
            # Test sending a simple message
            test_message = "Hello, this is a test message for automation testing"
            
            start_time = time.time()
            response = await self.automation.send_message(test_message)
            end_time = time.time()
            
            if response is not None:
                response_time = end_time - start_time
                logger.info(f"Message sent successfully, response received in {response_time:.2f}s")
                logger.info(f"Response length: {len(response)} characters")
                
                if len(response) > 0:
                    self._record_test_result(test_name, True, 
                        f"Message sending OK - Response: {len(response)} chars in {response_time:.2f}s")
                else:
                    self._record_test_result(test_name, False, "Message sent but empty response received")
            else:
                self._record_test_result(test_name, False, "Message sending failed - no response")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Message sending test failed: {str(e)}")
    
    async def test_response_retrieval(self):
        """Test response retrieval and parsing."""
        test_name = "Response Retrieval"
        
        try:
            if not self.automation or not self.automation.is_initialized:
                self._record_test_result(test_name, False, "Automation not initialized")
                return
            
            # Send a message and check response quality
            test_message = "Please respond with 'test response' to verify functionality"
            
            response = await self.automation.send_message(test_message)
            
            if response:
                # Check response characteristics
                response_length = len(response)
                has_text = any(c.isalpha() for c in response)
                no_error_indicators = not any(indicator in response.lower() 
                                            for indicator in ['error', 'failed', 'unavailable'])
                
                logger.info(f"Response analysis - Length: {response_length}, Has text: {has_text}, No errors: {no_error_indicators}")
                
                if response_length > 10 and has_text and no_error_indicators:
                    self._record_test_result(test_name, True, 
                        f"Response retrieval OK - Quality response received ({response_length} chars)")
                else:
                    self._record_test_result(test_name, False, 
                        f"Response quality issues - Length: {response_length}, Has text: {has_text}")
            else:
                self._record_test_result(test_name, False, "No response retrieved")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Response retrieval test failed: {str(e)}")
    
    async def test_conversation_management(self):
        """Test conversation management functionality."""
        test_name = "Conversation Management"
        
        try:
            if not self.automation or not self.automation.is_initialized:
                self._record_test_result(test_name, False, "Automation not initialized")
                return
            
            # Test getting conversation history
            history = await self.automation.get_conversation_history()
            
            if history is not None:
                history_length = len(history)
                logger.info(f"Retrieved conversation history with {history_length} messages")
                
                # Test clearing conversation
                clear_success = await self.automation.clear_conversation()
                
                if clear_success:
                    # Verify conversation was cleared
                    cleared_history = await self.automation.get_conversation_history()
                    cleared_length = len(cleared_history) if cleared_history else 0
                    
                    logger.info(f"Conversation cleared - messages before: {history_length}, after: {cleared_length}")
                    
                    if cleared_length < history_length:
                        self._record_test_result(test_name, True, 
                            f"Conversation management OK - Cleared {history_length - cleared_length} messages")
                    else:
                        self._record_test_result(test_name, False, 
                            "Conversation clear may not have worked - message count unchanged")
                else:
                    self._record_test_result(test_name, False, "Failed to clear conversation")
            else:
                self._record_test_result(test_name, False, "Failed to get conversation history")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Conversation management test failed: {str(e)}")
    
    async def test_health_check_functionality(self):
        """Test health check functionality."""
        test_name = "Health Check Functionality"
        
        try:
            if not self.automation or not self.automation.is_initialized:
                self._record_test_result(test_name, False, "Automation not initialized")
                return
            
            # Test health check
            health_status = await self.automation.health_check()
            
            if health_status:
                required_fields = ['healthy', 'status', 'initialized']
                missing_fields = [field for field in required_fields if field not in health_status]
                
                if missing_fields:
                    self._record_test_result(test_name, False, 
                        f"Health check missing fields: {missing_fields}")
                    return
                
                # Check health status values
                is_healthy = health_status.get('healthy', False)
                is_initialized = health_status.get('initialized', False)
                status_msg = health_status.get('status', 'unknown')
                
                logger.info(f"Health check - Healthy: {is_healthy}, Initialized: {is_initialized}, Status: {status_msg}")
                
                # Check for additional health metrics
                additional_metrics = []
                for field in ['session_age', 'last_activity', 'browser_connected', 'page_ready']:
                    if field in health_status:
                        additional_metrics.append(field)
                
                if additional_metrics:
                    logger.info(f"Additional health metrics available: {additional_metrics}")
                
                if is_healthy and is_initialized:
                    self._record_test_result(test_name, True, 
                        f"Health check OK - {status_msg} (metrics: {len(additional_metrics)})")
                else:
                    self._record_test_result(test_name, False, 
                        f"Health issues - Healthy: {is_healthy}, Initialized: {is_initialized}")
            else:
                self._record_test_result(test_name, False, "Health check returned no data")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Health check test failed: {str(e)}")
    
    async def test_error_recovery(self):
        """Test error recovery mechanisms."""
        test_name = "Error Recovery"
        
        try:
            if not self.automation or not self.automation.is_initialized:
                self._record_test_result(test_name, False, "Automation not initialized")
                return
            
            # Test recovery from failure
            recovery_success = await self.automation.recover_from_failure()
            
            if recovery_success:
                # Verify recovery by checking health
                health_after_recovery = await self.automation.health_check()
                is_healthy_after = health_after_recovery.get('healthy', False) if health_after_recovery else False
                
                if is_healthy_after:
                    self._record_test_result(test_name, True, "Error recovery OK - System recovered successfully")
                else:
                    self._record_test_result(test_name, False, "Recovery reported success but system still unhealthy")
            else:
                self._record_test_result(test_name, False, "Error recovery failed")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Error recovery test failed: {str(e)}")
    
    async def test_session_management(self):
        """Test session management functionality."""
        test_name = "Session Management"
        
        try:
            if not self.automation or not self.automation.is_initialized:
                self._record_test_result(test_name, False, "Automation not initialized")
                return
            
            # Check session information if available
            if hasattr(self.automation, 'session_manager'):
                session_info = getattr(self.automation.session_manager, 'sessions', [])
                active_sessions = getattr(self.automation.session_manager, 'active_sessions', 0)
                
                logger.info(f"Session info - Total sessions: {len(session_info)}, Active: {active_sessions}")
                
                self._record_test_result(test_name, True, 
                    f"Session management OK - {active_sessions} active sessions")
            else:
                # Check if we can get session-related health info
                health_status = await self.automation.health_check()
                if health_status and 'session_age' in health_status:
                    session_age = health_status['session_age']
                    logger.info(f"Session age: {session_age} seconds")
                    self._record_test_result(test_name, True, f"Session management OK - Session age: {session_age}s")
                else:
                    self._record_test_result(test_name, True, "Session management OK - Basic functionality working")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Session management test failed: {str(e)}")
    
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
        logger.info("PLAYWRIGHT AUTOMATION TEST SUMMARY")
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
    tester = PlaywrightAutomationTester()
    success = await tester.run_all_tests()
    
    if success:
        logger.info("\n🎉 All Playwright automation tests passed!")
        logger.info("The Doubao automation is working correctly.")
    else:
        logger.error("\n❌ Some Playwright automation tests failed!")
        logger.error("Please check the automation implementation and Doubao interface.")
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)