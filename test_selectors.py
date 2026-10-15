#!/usr/bin/env python3
"""
Test script to validate CSS selectors for Doubao automation.
This script tests the updated selectors against the Doubao interface.
"""

import asyncio
import logging
from doubao_automation import DoubaoAutomation
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_selectors():
    """Test the updated CSS selectors."""
    automation = DoubaoAutomation()
    
    try:
        # Initialize the automation
        logger.info("Initializing Doubao automation...")
        success = await automation.initialize()
        if not success:
            logger.error("Failed to initialize automation")
            return
        
        logger.info("Testing CSS selectors...")
        
        # Test input field selector
        input_selectors = [
            "textarea[placeholder*='输入']",
            "textarea[placeholder*='message']", 
            ".semi-input",
            ".input-area",
            "[data-testid*='input']",
            "[class*='input'][class*='textarea']"
        ]
        
        input_found = False
        for selector in input_selectors:
            try:
                element = await automation.page.query_selector(selector)
                if element:
                    logger.info(f"✓ Input field found with selector: {selector}")
                    input_found = True
                    break
            except Exception as e:
                logger.debug(f"Input selector {selector} failed: {e}")
        
        if not input_found:
            logger.warning("❌ No input field found with any selector")
        
        # Test send button selectors
        send_selectors = [
            "button[class*='send']",
            ".send-btn",
            "[data-testid*='send']",
            "button[type='submit']",
            ".semi-button[class*='send']",
            "[aria-label*='发送']",
            "[aria-label*='send']"
        ]
        
        send_found = False
        for selector in send_selectors:
            try:
                element = await automation.page.query_selector(selector)
                if element:
                    logger.info(f"✓ Send button found with selector: {selector}")
                    send_found = True
                    break
            except Exception as e:
                logger.debug(f"Send selector {selector} failed: {e}")
        
        if not send_found:
            logger.warning("❌ No send button found with any selector")
        
        # Test message container selectors
        message_selectors = [
            ".message-item",
            ".chat-message",
            "[class*='message'][class*='item']",
            "[data-testid*='message']",
            ".semi-chat-message",
            "[class*='chat'][class*='bubble']"
        ]
        
        message_found = False
        for selector in message_selectors:
            try:
                elements = await automation.page.query_selector_all(selector)
                if elements:
                    logger.info(f"✓ Message elements found with selector: {selector} ({len(elements)} elements)")
                    message_found = True
                    break
            except Exception as e:
                logger.debug(f"Message selector {selector} failed: {e}")
        
        if not message_found:
            logger.info("ℹ No message elements found (this may be normal for a fresh chat)")
        
        # Test clear button selectors
        clear_selectors = [
            "button[aria-label*='clear']",
            "button[aria-label*='new']",
            "button[aria-label*='重置']",
            "button[aria-label*='新建']",
            ".clear-button",
            ".new-chat-button",
            ".reset-btn",
            "[data-testid*='new-chat']",
            "[class*='new'][class*='chat']"
        ]
        
        clear_found = False
        for selector in clear_selectors:
            try:
                element = await automation.page.query_selector(selector)
                if element:
                    logger.info(f"✓ Clear button found with selector: {selector}")
                    clear_found = True
                    break
            except Exception as e:
                logger.debug(f"Clear selector {selector} failed: {e}")
        
        if not clear_found:
            logger.info("ℹ No clear button found (this may be normal)")
        
        # Test loading indicator selectors
        loading_selectors = [
            ".loading",
            ".spinner",
            "[class*='loading']",
            "[class*='spinner']",
            "[data-testid*='loading']",
            ".semi-spin",
            "[aria-busy='true']",
            ".typing-indicator",
            "[class*='typing']"
        ]
        
        loading_found = False
        for selector in loading_selectors:
            try:
                element = await automation.page.query_selector(selector)
                if element:
                    logger.info(f"✓ Loading indicator found with selector: {selector}")
                    loading_found = True
                    break
            except Exception as e:
                logger.debug(f"Loading selector {selector} failed: {e}")
        
        if not loading_found:
            logger.info("ℹ No loading indicators found (this may be normal)")
        
        logger.info("\n" + "="*50)
        logger.info("SELECTOR TEST SUMMARY:")
        logger.info("="*50)
        logger.info(f"Input field: {'✓ Found' if input_found else '❌ Not found'}")
        logger.info(f"Send button: {'✓ Found' if send_found else '❌ Not found'}")
        logger.info(f"Message elements: {'✓ Found' if message_found else 'ℹ Not found (may be normal)'}")
        logger.info(f"Clear button: {'✓ Found' if clear_found else 'ℹ Not found (may be normal)'}")
        logger.info(f"Loading indicators: {'✓ Found' if loading_found else 'ℹ Not found (may be normal)'}")
        
        # Test basic functionality
        logger.info("\nTesting basic functionality...")
        
        # Try to send a test message
        try:
            test_message = "Hello, this is a test message for selector validation."
            response = await automation.send_message(test_message)
            if response:
                logger.info("✓ Successfully sent test message and received response")
            else:
                logger.warning("⚠ Test message sent but no response received")
        except Exception as e:
            logger.error(f"❌ Failed to send test message: {e}")
        
        # Try to get conversation history
        try:
            history = await automation.get_conversation_history()
            logger.info(f"✓ Retrieved conversation history ({len(history)} messages)")
        except Exception as e:
            logger.error(f"❌ Failed to get conversation history: {e}")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
    
    finally:
        # Clean up
        logger.info("Cleaning up...")
        await automation.close()
        logger.info("Test completed.")

if __name__ == "__main__":
    asyncio.run(test_selectors())