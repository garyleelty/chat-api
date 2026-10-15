import asyncio
import logging
import time
import os
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Page, BrowserContext, TimeoutError, Error as PlaywrightError
from config import settings
import backoff
from dataclasses import dataclass
from enum import Enum


class AutomationErrorType(Enum):
    """Types of automation errors for better error handling."""
    INITIALIZATION_FAILED = "initialization_failed"
    BROWSER_CRASH = "browser_crash"
    TIMEOUT_ERROR = "timeout_error"
    ELEMENT_NOT_FOUND = "element_not_found"
    NETWORK_ERROR = "network_error"
    SESSION_EXPIRED = "session_expired"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class AutomationError(Exception):
    """Custom exception for automation errors with detailed information."""
    error_type: AutomationErrorType
    message: str
    detail: Optional[str] = None
    retry_after: Optional[int] = None
    original_exception: Optional[Exception] = None

    def __str__(self):
        return f"{self.error_type.value}: {self.message}"


class BrowserSessionManager:
    """Manages browser sessions with connection pooling and health checks."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, max_sessions: int = 5, session_timeout: int = 3600):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, max_sessions: int = 5, session_timeout: int = 3600):
        if self._initialized:
            return
        self._initialized = True
        
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.sessions: List[Dict[str, Any]] = []
        self.active_sessions = 0
        self.logger = logging.getLogger(__name__)
        
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
        
        self._user_data_dir = os.path.join(os.path.dirname(__file__), "browser_data")
        os.makedirs(self._user_data_dir, exist_ok=True)
    
    async def create_session(self) -> tuple[Browser, Page]:
        """Create or reuse browser session with persistent context."""
        try:
            if self._page and not self._page.is_closed():
                try:
                    await self._page.wait_for_selector("body", timeout=1000)
                    self.logger.info("Reusing existing browser session")
                    return self._browser, self._page
                except:
                    self.logger.info("Existing page is not usable, creating new one")
            
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            
            launch_options = {
                "headless": settings.BROWSER.HEADLESS,
                "slow_mo": settings.BROWSER.SLOW_MO,
                "args": self._get_browser_args(),
                "channel": "chrome"
            }
            
            if self._browser is None:
                self._browser = await self._playwright.chromium.launch(**launch_options)
            
            if self._context is None:
                self._context = await self._browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=self._get_user_agent(),
                    device_scale_factor=1.0,
                    is_mobile=False,
                    has_touch=False
                )
                self._context.set_default_timeout(settings.BROWSER.TIMEOUT)
                self._context.set_default_navigation_timeout(settings.BROWSER.TIMEOUT)
            
            if self._page is None or self._page.is_closed():
                self._page = await self._context.new_page()
            
            session_info = {
                "browser": self._browser,
                "page": self._page,
                "created_at": time.time(),
                "context": self._context,
                "playwright": self._playwright
            }
            
            if not any(s.get("page") == self._page for s in self.sessions):
                self.sessions.append(session_info)
                self.active_sessions += 1
            
            self.logger.info(f"Browser session ready. Active sessions: {self.active_sessions}")
            return self._browser, self._page
            
        except Exception as e:
            self.logger.error(f"Failed to create browser session: {str(e)}")
            raise AutomationError(
                error_type=AutomationErrorType.INITIALIZATION_FAILED,
                message="Failed to create browser session",
                detail=str(e),
                original_exception=e
            )
    
    def _get_browser_args(self) -> List[str]:
        """Get browser launch arguments based on environment."""
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-features=IsolateOrigins",
            "--disable-site-isolation-trials"
        ]
        
        if settings.DEBUG:
            args.append("--auto-open-devtools-for-tabs")
        
        return args
    
    def _get_user_agent(self) -> str:
        """Get user agent string."""
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    
    async def close_session(self, browser: Browser = None, page: Page = None, context = None, playwright = None, force: bool = False) -> None:
        """Close browser session and cleanup resources.
        
        Args:
            force: If True, completely close the browser. If False, just reset references.
        """
        try:
            if not force:
                self.logger.info("Keeping browser session alive for reuse")
                return
            
            if self._page and not self._page.is_closed():
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            
            self.active_sessions = 0
            self.sessions = []
            self.logger.info("Browser session completely closed")
            
        except Exception as e:
            self.logger.error(f"Error closing browser session: {str(e)}")
    
    async def force_close(self) -> None:
        """Force close all browser resources."""
        await self.close_session(force=True)
    
    def cleanup_expired_sessions(self) -> None:
        """Remove expired sessions from tracking."""
        current_time = time.time()
        expired_sessions = [
            session for session in self.sessions
            if current_time - session["created_at"] > self.session_timeout
        ]
        
        for session in expired_sessions:
            self.sessions.remove(session)
            self.active_sessions = max(0, self.active_sessions - 1)
        
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")


# Global session manager instance
session_manager = BrowserSessionManager(
    max_sessions=settings.SESSION.MAX_SESSIONS,
    session_timeout=settings.SESSION.SESSION_TIMEOUT
)


class DoubaoAutomation:
    """Handles browser automation for Doubao chat interactions with enhanced error handling."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context = None
        self.playwright = None
        self.is_initialized = False
        self.session_start_time = None
        self.last_activity_time = None
        self.retry_count = 0
        self.max_retries = 3
    
    @backoff.on_exception(
        backoff.expo,
        (AutomationError, PlaywrightError, TimeoutError),
        max_tries=3,
        max_time=300,
        on_backoff=lambda details: logging.getLogger(__name__).warning(
            f"Retrying initialization (attempt {details['tries']}/3) after error: {details.get('exception', 'Unknown error')}"
        )
    )
    async def initialize(self) -> bool:
        """Initialize the browser and navigate to Doubao with retry mechanism."""
        self.session_start_time = time.time()
        self.last_activity_time = time.time()
        
        try:
            # Use session manager to create browser session
            self.browser, self.page = await session_manager.create_session()
            
            # Get additional session objects
            for session in session_manager.sessions:
                if session["browser"] == self.browser:
                    self.context = session["context"]
                    self.playwright = session["playwright"]
                    break
            
            # Navigate to Doubao with enhanced error handling
            navigation_success = await self._safe_navigate(settings.DOUBAO_URL)
            
            if not navigation_success:
                raise AutomationError(
                    error_type=AutomationErrorType.NETWORK_ERROR,
                    message="Failed to navigate to Doubao URL",
                    detail=f"Could not reach {settings.DOUBAO_URL}"
                )
            
            # Wait for page to be ready
            await self._wait_for_page_ready()
            
            self.is_initialized = True
            self.retry_count = 0
            self.logger.info("Successfully initialized Doubao automation")
            return True
            
        except AutomationError:
            # Re-raise AutomationError as-is for backoff to handle
            raise
        except PlaywrightError as e:
            self.logger.error(f"Playwright error during initialization: {str(e)}")
            raise AutomationError(
                error_type=AutomationErrorType.BROWSER_CRASH,
                message="Browser automation error",
                detail=str(e),
                original_exception=e
            )
        except TimeoutError as e:
            self.logger.error(f"Timeout during initialization: {str(e)}")
            raise AutomationError(
                error_type=AutomationErrorType.TIMEOUT_ERROR,
                message="Initialization timeout",
                detail=str(e),
                retry_after=30,
                original_exception=e
            )
        except Exception as e:
            self.logger.error(f"Unexpected error during initialization: {str(e)}", exc_info=True)
            raise AutomationError(
                error_type=AutomationErrorType.UNKNOWN_ERROR,
                message="Unexpected initialization error",
                detail=str(e),
                original_exception=e
            )
    
    async def _safe_navigate(self, url: str, max_attempts: int = 3) -> bool:
        """Safely navigate to URL with retry logic."""
        for attempt in range(max_attempts):
            try:
                response = await self.page.goto(url, timeout=settings.BROWSER.TIMEOUT)
                
                if response and response.status == 200:
                    self.logger.info(f"Successfully navigated to {url}")
                    return True
                elif response:
                    self.logger.warning(f"Navigation to {url} returned status {response.status}")
                else:
                    self.logger.warning(f"No response received when navigating to {url}")
                
            except TimeoutError:
                self.logger.warning(f"Navigation timeout (attempt {attempt + 1}/{max_attempts})")
                if attempt == max_attempts - 1:
                    return False
            except Exception as e:
                self.logger.warning(f"Navigation error (attempt {attempt + 1}/{max_attempts}): {str(e)}")
                if attempt == max_attempts - 1:
                    return False
            
            await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
        
        return False
    
    async def _wait_for_page_ready(self, timeout: int = 30000) -> bool:
        """Wait for page to be fully loaded and ready."""
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            
            await self.page.screenshot(path="/tmp/doubao_page.png")
            self.logger.info("Screenshot saved to /tmp/doubao_page.png")
            
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            essential_selectors = [
                "textarea",
                "input",
                ".chat-container",
                ".message-area",
                "[class*='input']",
                "[class*='chat']"
            ]
            
            for selector in essential_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    self.logger.debug(f"Found essential element: {selector}")
                    break
                except TimeoutError:
                    continue
            
            self.last_activity_time = time.time()
            return True
            
        except Exception as e:
            self.logger.warning(f"Page ready check failed: {str(e)}")
            return False
    
    @backoff.on_exception(
        backoff.expo,
        (AutomationError, PlaywrightError, TimeoutError),
        max_tries=3,
        max_time=120,
        on_backoff=lambda details: logging.getLogger(__name__).warning(
            f"Retrying send_message (attempt {details['tries']}/3) after error: {details.get('exception', 'Unknown error')}"
        )
    )
    async def send_message(self, message: str) -> Optional[str]:
        """Send a message to Doubao and get the response with enhanced error handling."""
        if not self.is_initialized or not self.page:
            raise AutomationError(
                error_type=AutomationErrorType.SESSION_EXPIRED,
                message="Automation not initialized",
                detail="Call initialize() first or session has expired"
            )
        
        # Validate message
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        
        if len(message) > settings.MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message exceeds maximum length of {settings.MAX_MESSAGE_LENGTH}")
        
        self.last_activity_time = time.time()
        
        try:
            # Check if session is still healthy
            if not await self._check_session_health():
                raise AutomationError(
                    error_type=AutomationErrorType.SESSION_EXPIRED,
                    message="Browser session is unhealthy",
                    detail="Session health check failed"
                )
            
            # Wait for input field and type message
            input_selector = self._get_input_selector()
            input_element = await self._wait_for_element(input_selector, "input field")
            
            if not input_element:
                all_inputs = await self.page.query_selector_all("input, textarea, [contenteditable='true'], [role='textbox']")
                self.logger.info(f"Found {len(all_inputs)} potential input elements on page")
                for i, el in enumerate(all_inputs[:5]):
                    tag = await el.evaluate("el => el.tagName")
                    cls = await el.get_attribute("class") or ""
                    self.logger.info(f"Element {i}: tag={tag}, class={cls[:50]}")
                
                raise AutomationError(
                    error_type=AutomationErrorType.ELEMENT_NOT_FOUND,
                    message="Could not find input element",
                    detail=f"None of the input selectors matched: {input_selector}"
                )
            
            is_contenteditable = await input_element.get_attribute("contenteditable")
            
            if is_contenteditable == "true":
                await input_element.click()
                await self.page.keyboard.press("Control+A")
                await self.page.keyboard.type(message, delay=10)
            else:
                await input_element.fill("")
                await input_element.fill(message)
            
            # Look for send button or press Enter
            send_button_selector = self._get_send_button_selector()
            send_button = await self.page.query_selector(send_button_selector)
            
            if send_button:
                await send_button.click()
            else:
                await input_element.press("Enter")
            
            await asyncio.sleep(1)
            
            response = await self._wait_for_response()
            
            if response is None:
                # Try refreshing the page and retrying once
                self.logger.warning("No response received, attempting page refresh")
                await self._emergency_refresh()
                return await self._retry_send_message(message)
            
            self.retry_count = 0
            return response
            
        except AutomationError:
            # Re-raise for backoff handling
            raise
        except PlaywrightError as e:
            self.logger.error(f"Playwright error sending message: {str(e)}")
            raise AutomationError(
                error_type=AutomationErrorType.BROWSER_CRASH,
                message="Browser automation error during message send",
                detail=str(e),
                original_exception=e
            )
        except TimeoutError as e:
            self.logger.error(f"Timeout while waiting for response: {str(e)}")
            raise AutomationError(
                error_type=AutomationErrorType.TIMEOUT_ERROR,
                message="Response timeout",
                detail=str(e),
                retry_after=10,
                original_exception=e
            )
        except Exception as e:
            self.logger.error(f"Unexpected error sending message: {str(e)}", exc_info=True)
            raise AutomationError(
                error_type=AutomationErrorType.UNKNOWN_ERROR,
                message="Unexpected error during message send",
                detail=str(e),
                original_exception=e
            )
    
    def _get_input_selector(self) -> str:
        return (
            "textarea.semi-input-textarea, "
            ".semi-input-textarea, "
            "textarea[placeholder*='发消息'], "
            "textarea[data-testid*='chat_input'], "
            "textarea[class*='chat'], textarea[class*='message']"
        )
    
    def _get_send_button_selector(self) -> str:
        """Get the send button selector."""
        return (
            "button[class*='send'], .send-btn, [data-testid*='send'], "
            "button[type='submit'], .semi-button[class*='send'], "
            "[aria-label*='发送'], [aria-label*='send'], "
            "button[class*='submit'], button[class*='chat-send']"
        )
    
    async def _wait_for_element(self, selector: str, element_name: str, timeout: int = None) -> Optional[Any]:
        """Wait for element with enhanced error handling."""
        try:
            timeout = timeout or settings.BROWSER.TIMEOUT
            await self.page.wait_for_selector(selector, timeout=timeout)
            return await self.page.query_selector(selector)
        except TimeoutError:
            self.logger.warning(f"Timeout waiting for {element_name}")
            return None
        except Exception as e:
            self.logger.warning(f"Error waiting for {element_name}: {str(e)}")
            return None
    
    async def _wait_for_response(self, timeout: int = None) -> Optional[str]:
        """Wait for response with enhanced selectors and timeout handling."""
        try:
            timeout = timeout or settings.BROWSER.TIMEOUT
            
            response_selector = self._get_response_selector()
            
            await asyncio.sleep(2)
            await self.wait_for_loading_complete(timeout=10000)
            
            response_elements = await self.page.query_selector_all(response_selector)
            
            if response_elements:
                last_response = response_elements[-1]
                response_text = await last_response.text_content()
                if response_text:
                    return response_text.strip()
            
            return None
            
        except TimeoutError:
            self.logger.warning("Timeout waiting for response")
            return None
        except Exception as e:
            self.logger.warning(f"Error waiting for response: {str(e)}")
            return None
    
    def _get_response_selector(self) -> str:
        """Get the response selector."""
        return (
            ".auto-hide-last-sibling-br.paragraph-pP9ZLC, "
            "div.auto-hide-last-sibling-br, "
            "[class*='paragraph-element'], "
            ".chat-message-assistant .paragraph-pP9ZLC, "
            "[data-role='assistant'] .paragraph-pP9ZLC, "
            ".assistant-message .paragraph-pP9ZLC"
        )
    
    async def _check_session_health(self) -> bool:
        """Check if the browser session is still healthy."""
        try:
            if not self.browser or not self.page:
                return False
            
            # Check if page is still connected
            await self.page.evaluate("1+1")
            
            # Check session age
            session_age = time.time() - self.session_start_time
            if session_age > settings.SESSION.SESSION_TIMEOUT:
                self.logger.warning(f"Session age ({session_age}s) exceeds timeout")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Session health check failed: {str(e)}")
            return False
    
    async def _emergency_refresh(self) -> bool:
        """Emergency page refresh to recover from issues."""
        try:
            self.logger.info("Performing emergency page refresh")
            await self.page.reload(timeout=settings.BROWSER.TIMEOUT)
            await self._wait_for_page_ready()
            return True
        except Exception as e:
            self.logger.error(f"Emergency refresh failed: {str(e)}")
            return False
    
    async def _retry_send_message(self, message: str) -> Optional[str]:
        """Retry sending message after recovery attempts."""
        try:
            self.retry_count += 1
            if self.retry_count > self.max_retries:
                self.logger.error("Max retries exceeded for send_message")
                return None
            
            self.logger.info(f"Retrying send_message (attempt {self.retry_count})")
            return await self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Retry attempt {self.retry_count} failed: {str(e)}")
            return None
    
    async def get_conversation_history(self) -> list:
        """Get the current conversation history with error handling."""
        if not self.is_initialized or not self.page:
            raise AutomationError(
                error_type=AutomationErrorType.SESSION_EXPIRED,
                message="Automation not initialized",
                detail="Call initialize() first or session has expired"
            )
        
        try:
            # Check session health first
            if not await self._check_session_health():
                raise AutomationError(
                    error_type=AutomationErrorType.SESSION_EXPIRED,
                    message="Browser session is unhealthy"
                )
            
            message_selector = self._get_response_selector()
            message_elements = await self.page.query_selector_all(message_selector)
            
            history = []
            for element in message_elements:
                try:
                    text = await element.text_content()
                    if text and text.strip():
                        history.append(text.strip())
                except Exception as e:
                    self.logger.debug(f"Error extracting message text: {str(e)}")
                    continue
            
            self.last_activity_time = time.time()
            return history
            
        except AutomationError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {str(e)}", exc_info=True)
            return []
    
    async def clear_conversation(self) -> bool:
        """Clear the current conversation with enhanced error handling."""
        if not self.is_initialized or not self.page:
            raise AutomationError(
                error_type=AutomationErrorType.SESSION_EXPIRED,
                message="Automation not initialized",
                detail="Call initialize() first or session has expired"
            )
        
        try:
            # Check session health first
            if not await self._check_session_health():
                raise AutomationError(
                    error_type=AutomationErrorType.SESSION_EXPIRED,
                    message="Browser session is unhealthy"
                )
            
            # Look for clear/reset button
            clear_selectors = [
                "button[aria-label*='clear']",
                "button[aria-label*='new']",
                "button[aria-label*='重置']",
                "button[aria-label*='新建']",
                ".clear-button",
                ".new-chat-button",
                ".reset-btn",
                "[data-testid*='new-chat']",
                "[class*='new'][class*='chat']",
                "[class*='clear'][class*='chat']"
            ]
            
            for selector in clear_selectors:
                try:
                    clear_button = await self.page.query_selector(selector)
                    if clear_button:
                        await clear_button.click()
                        await asyncio.sleep(1)  # Wait for UI to update
                        
                        # Confirm the clear action if confirmation dialog appears
                        if await self.page.query_selector("button:has-text('确认')"):
                            await self.page.click("button:has-text('确认')")
                        
                        self.logger.info("Successfully cleared conversation")
                        self.last_activity_time = time.time()
                        return True
                except Exception as e:
                    self.logger.debug(f"Error with clear selector {selector}: {str(e)}")
                    continue
            
            # If no clear button found, try refreshing the page
            self.logger.info("No clear button found, refreshing page")
            await self.page.reload(timeout=settings.BROWSER.TIMEOUT)
            await self._wait_for_page_ready()
            
            self.last_activity_time = time.time()
            return True
            
        except AutomationError:
            raise
        except Exception as e:
            self.logger.error(f"Error clearing conversation: {str(e)}", exc_info=True)
            return False

    async def wait_for_loading_complete(self, timeout: int = 30000) -> bool:
        """Wait for loading indicators to disappear with enhanced error handling."""
        if not self.is_initialized or not self.page:
            raise AutomationError(
                error_type=AutomationErrorType.SESSION_EXPIRED,
                message="Automation not initialized",
                detail="Call initialize() first or session has expired"
            )
        
        try:
            # Check session health first
            if not await self._check_session_health():
                raise AutomationError(
                    error_type=AutomationErrorType.SESSION_EXPIRED,
                    message="Browser session is unhealthy"
                )
            
            # Loading indicators to wait for
            loading_selectors = [
                ".loading",
                ".spinner",
                "[class*='loading']",
                "[class*='spinner']",
                "[data-testid*='loading']",
                ".semi-spin",
                "[aria-busy='true']",
                ".typing-indicator",
                "[class*='typing']",
                ".loader",
                "[class*='loader']",
                ".progress-bar",
                "[class*='progress']"
            ]
            
            # Wait for loading indicators to disappear
            for selector in loading_selectors:
                try:
                    await self.page.wait_for_selector(selector, state="detached", timeout=timeout // 3)
                except TimeoutError:
                    # If timeout, check if element still exists
                    element = await self.page.query_selector(selector)
                    if not element:
                        continue
                    # Element still exists after timeout, log warning
                    self.logger.warning(f"Loading indicator '{selector}' still present after timeout")
                except Exception as e:
                    self.logger.debug(f"Error waiting for loading indicator '{selector}': {str(e)}")
                    continue
            
            # Additional wait for network idle
            try:
                await self.page.wait_for_load_state("networkidle", timeout=timeout // 3)
            except Exception:
                pass  # Network idle is optional
            
            self.last_activity_time = time.time()
            return True
            
        except AutomationError:
            raise
        except Exception as e:
            self.logger.error(f"Error waiting for loading to complete: {str(e)}", exc_info=True)
            return False
    
    async def close(self, force: bool = False):
        """Close the browser and cleanup resources gracefully.
        
        Args:
            force: If True, completely close the browser. If False, keep session for reuse.
        """
        try:
            self.logger.info("Closing Doubao automation...")
            
            if self.browser and self.context and self.playwright:
                await session_manager.close_session(
                    self.browser, self.page, self.context, self.playwright,
                    force=force
                )
            
            if force:
                self.is_initialized = False
                self.browser = None
                self.page = None
                self.context = None
                self.playwright = None
                self.session_start_time = None
                self.last_activity_time = None
            
            self.logger.info("Successfully closed Doubao automation")
            
        except Exception as e:
            self.logger.error(f"Error closing browser: {str(e)}", exc_info=True)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of the automation instance."""
        health_status = {
            "healthy": False,
            "initialized": self.is_initialized,
            "session_age": 0,
            "last_activity": 0,
            "retry_count": self.retry_count,
            "browser_connected": False,
            "page_ready": False,
            "errors": []
        }
        
        try:
            if self.is_initialized:
                # Calculate session metrics
                current_time = time.time()
                health_status["session_age"] = current_time - (self.session_start_time or current_time)
                health_status["last_activity"] = current_time - (self.last_activity_time or current_time)
                
                # Check browser connection
                if self.browser:
                    try:
                        # Simple evaluation to check browser connectivity
                        await self.browser.contexts()
                        health_status["browser_connected"] = True
                    except Exception as e:
                        health_status["errors"].append(f"Browser connection error: {str(e)}")
                
                # Check page readiness
                if self.page:
                    try:
                        await self.page.evaluate("1+1")
                        health_status["page_ready"] = True
                    except Exception as e:
                        health_status["errors"].append(f"Page evaluation error: {str(e)}")
                
                # Determine overall health
                health_status["healthy"] = (
                    health_status["browser_connected"] and
                    health_status["page_ready"] and
                    health_status["session_age"] < settings.SESSION.SESSION_TIMEOUT
                )
            
        except Exception as e:
            health_status["errors"].append(f"Health check error: {str(e)}")
            self.logger.error(f"Health check failed: {str(e)}", exc_info=True)
        
        return health_status
    
    async def recover_from_failure(self) -> bool:
        """Attempt to recover from a failure state."""
        try:
            self.logger.warning("Attempting to recover from failure state")
            
            # Check if we need full reinitialization
            if not self.is_initialized or not self.browser:
                self.logger.info("Performing full reinitialization")
                return await self.initialize()
            
            # Try emergency refresh first
            if await self._emergency_refresh():
                self.logger.info("Recovery successful via emergency refresh")
                return True
            
            # If refresh fails, try full reinitialization
            self.logger.info("Emergency refresh failed, attempting full reinitialization")
            await self.close()
            return await self.initialize()
            
        except Exception as e:
            self.logger.error(f"Recovery failed: {str(e)}", exc_info=True)
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Factory function for creating automation instances
async def create_doubao_automation(max_retries: int = 3) -> DoubaoAutomation:
    """Create and initialize a new Doubao automation instance with retry logic."""
    logger = logging.getLogger(__name__)
    automation = DoubaoAutomation()
    automation.max_retries = max_retries
    
    for attempt in range(max_retries):
        try:
            success = await automation.initialize()
            if success:
                return automation
            
            logger.warning(f"Initialization attempt {attempt + 1}/{max_retries} failed")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
        except AutomationError as e:
            logger.error(f"Automation error during initialization (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(e.retry_after or 5)
        except Exception as e:
            logger.error(f"Unexpected error during initialization (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                raise AutomationError(
                    error_type=AutomationErrorType.INITIALIZATION_FAILED,
                    message="Failed to initialize Doubao automation after all retries",
                    detail=str(e),
                    original_exception=e
                )
            await asyncio.sleep(5)
    
    raise AutomationError(
        error_type=AutomationErrorType.INITIALIZATION_FAILED,
        message="Failed to initialize Doubao automation"
    )
