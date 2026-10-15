#!/usr/bin/env python3
"""
Configuration Validation Tests for Doubao Chat API

This module contains comprehensive tests to validate the configuration
system including environment-specific settings, validation rules,
and configuration loading mechanisms.
"""

import os
import sys
import logging
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigurationTester:
    """Test suite for configuration validation."""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.original_env = {}
        
    def setup(self):
        """Setup test environment."""
        # Store original environment variables
        self.original_env = {
            'ENVIRONMENT': os.environ.get('ENVIRONMENT'),
            'DEBUG': os.environ.get('DEBUG'),
            'PORT': os.environ.get('PORT'),
            'DOUBAO_URL': os.environ.get('DOUBAO_URL'),
            'LOG_LEVEL': os.environ.get('LOG_LEVEL'),
        }
    
    def teardown(self):
        """Restore original environment."""
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
    
    def run_all_tests(self) -> bool:
        """Run all configuration validation tests."""
        logger.info("Starting configuration validation tests...")
        
        self.setup()
        
        try:
            # Test basic configuration loading
            self.test_basic_configuration_loading()
            
            # Test environment-specific configurations
            self.test_environment_specific_configs()
            
            # Test configuration validation rules
            self.test_configuration_validation_rules()
            
            # Test browser configuration
            self.test_browser_configuration()
            
            # Test logging configuration
            self.test_logging_configuration()
            
            # Test session configuration
            self.test_session_configuration()
            
            # Test retry configuration
            self.test_retry_configuration()
            
            # Test health check configuration
            self.test_health_check_configuration()
            
            # Test environment variable loading
            self.test_environment_variable_loading()
            
            # Test configuration methods
            self.test_configuration_methods()
            
            # Test configuration edge cases
            self.test_configuration_edge_cases()
            
            # Generate summary
            return self.generate_summary()
            
        finally:
            self.teardown()
    
    def test_basic_configuration_loading(self):
        """Test basic configuration loading."""
        test_name = "Basic Configuration Loading"
        
        try:
            from config import Settings, settings
            
            # Test default settings creation
            default_settings = Settings()
            
            # Check required fields
            required_fields = [
                'ENVIRONMENT', 'PROJECT_NAME', 'VERSION', 'DEBUG', 'HOST', 'PORT',
                'DOUBAO_URL', 'BROWSER', 'LOGGING', 'SESSION', 'RETRY', 'HEALTH_CHECK'
            ]
            
            missing_fields = []
            for field in required_fields:
                if not hasattr(default_settings, field):
                    missing_fields.append(field)
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Missing required fields: {missing_fields}")
                return
            
            # Test field types and values
            validation_errors = []
            
            if not isinstance(default_settings.PORT, int):
                validation_errors.append("PORT should be integer")
            
            if not isinstance(default_settings.DEBUG, bool):
                validation_errors.append("DEBUG should be boolean")
            
            if not isinstance(default_settings.DOUBAO_URL, str):
                validation_errors.append("DOUBAO_URL should be string")
            
            if not default_settings.DOUBAO_URL.startswith('http'):
                validation_errors.append("DOUBAO_URL should be a valid URL")
            
            if validation_errors:
                self._record_test_result(test_name, False, f"Validation errors: {'; '.join(validation_errors)}")
                return
            
            logger.info(f"✓ Default settings loaded - Environment: {default_settings.ENVIRONMENT}, Port: {default_settings.PORT}")
            self._record_test_result(test_name, True, "Basic configuration loading working correctly")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Basic configuration loading failed: {str(e)}")
    
    def test_environment_specific_configs(self):
        """Test environment-specific configurations."""
        test_name = "Environment-Specific Configurations"
        
        try:
            from config import Settings, Environment
            
            environments = [
                Environment.DEVELOPMENT,
                Environment.PRODUCTION,
                Environment.TESTING,
                Environment.STAGING
            ]
            
            environment_results = []
            
            for env in environments:
                try:
                    # Set environment and create settings
                    test_settings = Settings(ENVIRONMENT=env)
                    
                    # Check environment-specific settings
                    if env == Environment.DEVELOPMENT:
                        if not test_settings.DEBUG:
                            environment_results.append(f"{env}: DEBUG should be True")
                        if not test_settings.BROWSER.HEADLESS:
                            environment_results.append(f"{env}: HEADLESS should be False")
                    
                    elif env == Environment.PRODUCTION:
                        if test_settings.DEBUG:
                            environment_results.append(f"{env}: DEBUG should be False")
                        if not test_settings.BROWSER.HEADLESS:
                            environment_results.append(f"{env}: HEADLESS should be True")
                    
                    elif env == Environment.TESTING:
                        if not test_settings.DEBUG:
                            environment_results.append(f"{env}: DEBUG should be True")
                    
                    logger.info(f"✓ Environment {env} configured correctly")
                    
                except Exception as e:
                    environment_results.append(f"{env}: {str(e)}")
            
            if environment_results:
                self._record_test_result(test_name, False, f"Environment config errors: {'; '.join(environment_results)}")
            else:
                self._record_test_result(test_name, True, f"All {len(environments)} environments configured correctly")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Environment-specific configuration test failed: {str(e)}")
    
    def test_configuration_validation_rules(self):
        """Test configuration validation rules."""
        test_name = "Configuration Validation Rules"
        
        try:
            from config import Settings, ValidationError
            
            validation_tests = [
                {
                    "description": "Invalid port number (too low)",
                    "settings_dict": {"PORT": 0},
                    "should_fail": True
                },
                {
                    "description": "Invalid port number (too high)",
                    "settings_dict": {"PORT": 70000},
                    "should_fail": True
                },
                {
                    "description": "Valid port number",
                    "settings_dict": {"PORT": 8080},
                    "should_fail": False
                },
                {
                    "description": "Invalid max message length",
                    "settings_dict": {"MAX_MESSAGE_LENGTH": 0},
                    "should_fail": True
                },
                {
                    "description": "Valid max message length",
                    "settings_dict": {"MAX_MESSAGE_LENGTH": 5000},
                    "should_fail": False
                },
                {
                    "description": "Invalid workers count",
                    "settings_dict": {"WORKERS": 0},
                    "should_fail": True
                },
                {
                    "description": "Valid workers count",
                    "settings_dict": {"WORKERS": 4},
                    "should_fail": False
                }
            ]
            
            validation_results = []
            
            for test_case in validation_tests:
                try:
                    settings = Settings(**test_case["settings_dict"])
                    
                    if test_case["should_fail"]:
                        validation_results.append(f"{test_case['description']}: Expected validation error but succeeded")
                    else:
                        logger.info(f"✓ Validation passed: {test_case['description']}")
                        
                except ValidationError as e:
                    if test_case["should_fail"]:
                        logger.info(f"✓ Validation correctly failed: {test_case['description']}")
                    else:
                        validation_results.append(f"{test_case['description']}: Unexpected validation error: {str(e)}")
                except Exception as e:
                    validation_results.append(f"{test_case['description']}: Unexpected error: {str(e)}")
            
            if validation_results:
                self._record_test_result(test_name, False, f"Validation rule errors: {'; '.join(validation_results)}")
            else:
                self._record_test_result(test_name, True, f"All validation rules working correctly")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Configuration validation rules test failed: {str(e)}")
    
    def test_browser_configuration(self):
        """Test browser configuration."""
        test_name = "Browser Configuration"
        
        try:
            from config import Settings, BrowserConfig
            
            # Test default browser config
            browser_config = BrowserConfig()
            
            # Check required browser fields
            browser_fields = [
                'BROWSER_TYPE', 'HEADLESS', 'SLOW_MO', 'TIMEOUT',
                'VIEWPORT_WIDTH', 'VIEWPORT_HEIGHT', 'USER_AGENT'
            ]
            
            missing_fields = []
            for field in browser_fields:
                if not hasattr(browser_config, field):
                    missing_fields.append(field)
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Missing browser fields: {missing_fields}")
                return
            
            # Test browser type validation
            valid_browser_types = ['chromium', 'firefox', 'webkit']
            if browser_config.BROWSER_TYPE not in valid_browser_types:
                self._record_test_result(test_name, False, f"Invalid browser type: {browser_config.BROWSER_TYPE}")
                return
            
            # Test timeout validation
            if not (1000 <= browser_config.TIMEOUT <= 300000):
                self._record_test_result(test_name, False, f"Timeout out of range: {browser_config.TIMEOUT}")
                return
            
            # Test settings browser args generation
            settings = Settings()
            browser_args = settings.get_browser_args()
            
            if not isinstance(browser_args, list):
                self._record_test_result(test_name, False, "Browser args should be a list")
                return
            
            if len(browser_args) == 0:
                self._record_test_result(test_name, False, "Browser args should not be empty")
                return
            
            logger.info(f"✓ Browser configuration valid - Type: {browser_config.BROWSER_TYPE}, Args: {len(browser_args)}")
            self._record_test_result(test_name, True, "Browser configuration working correctly")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Browser configuration test failed: {str(e)}")
    
    def test_logging_configuration(self):
        """Test logging configuration."""
        test_name = "Logging Configuration"
        
        try:
            from config import Settings, LoggingConfig, LogFormat
            
            # Test default logging config
            logging_config = LoggingConfig()
            
            # Check required logging fields
            logging_fields = [
                'LOG_LEVEL', 'LOG_FORMAT', 'LOG_FILE', 'LOG_ROTATION',
                'LOG_RETENTION', 'LOG_COMPRESSION', 'LOG_SERIALIZE'
            ]
            
            missing_fields = []
            for field in logging_fields:
                if not hasattr(logging_config, field):
                    missing_fields.append(field)
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Missing logging fields: {missing_fields}")
                return
            
            # Test log level validation
            valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if logging_config.LOG_LEVEL not in valid_log_levels:
                self._record_test_result(test_name, False, f"Invalid log level: {logging_config.LOG_LEVEL}")
                return
            
            # Test log format validation
            if not isinstance(logging_config.LOG_FORMAT, LogFormat):
                self._record_test_result(test_name, False, f"Invalid log format type: {type(logging_config.LOG_FORMAT)}")
                return
            
            # Test settings logging config generation
            settings = Settings()
            logging_config_dict = settings.get_logging_config()
            
            if not isinstance(logging_config_dict, dict):
                self._record_test_result(test_name, False, "Logging config should be a dictionary")
                return
            
            required_logging_keys = ['level', 'format', 'serialize']
            missing_keys = [key for key in required_logging_keys if key not in logging_config_dict]
            
            if missing_keys:
                self._record_test_result(test_name, False, f"Missing logging config keys: {missing_keys}")
                return
            
            logger.info(f"✓ Logging configuration valid - Level: {logging_config.LOG_LEVEL}, Format: {logging_config.LOG_FORMAT}")
            self._record_test_result(test_name, True, "Logging configuration working correctly")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Logging configuration test failed: {str(e)}")
    
    def test_session_configuration(self):
        """Test session configuration."""
        test_name = "Session Configuration"
        
        try:
            from config import Settings, SessionConfig
            
            # Test default session config
            session_config = SessionConfig()
            
            # Check required session fields
            session_fields = [
                'MAX_SESSIONS', 'SESSION_TIMEOUT', 'SESSION_CLEANUP_INTERVAL',
                'SESSION_MAX_AGE', 'SESSION_POOL_SIZE'
            ]
            
            missing_fields = []
            for field in session_fields:
                if not hasattr(session_config, field):
                    missing_fields.append(field)
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Missing session fields: {missing_fields}")
                return
            
            # Test session validation ranges
            validation_checks = [
                (1 <= session_config.MAX_SESSIONS <= 50, "MAX_SESSIONS out of range"),
                (300 <= session_config.SESSION_TIMEOUT <= 86400, "SESSION_TIMEOUT out of range"),
                (session_config.SESSION_POOL_SIZE >= 1, "SESSION_POOL_SIZE should be >= 1")
            ]
            
            validation_errors = []
            for check, error_msg in validation_checks:
                if not check:
                    validation_errors.append(error_msg)
            
            if validation_errors:
                self._record_test_result(test_name, False, f"Session validation errors: {'; '.join(validation_errors)}")
                return
            
            logger.info(f"✓ Session configuration valid - Max sessions: {session_config.MAX_SESSIONS}, Timeout: {session_config.SESSION_TIMEOUT}s")
            self._record_test_result(test_name, True, "Session configuration working correctly")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Session configuration test failed: {str(e)}")
    
    def test_retry_configuration(self):
        """Test retry configuration."""
        test_name = "Retry Configuration"
        
        try:
            from config import Settings, RetryConfig
            
            # Test default retry config
            retry_config = RetryConfig()
            
            # Check required retry fields
            retry_fields = [
                'MAX_RETRIES', 'INITIAL_RETRY_DELAY', 'MAX_RETRY_DELAY',
                'RETRY_BACKOFF_MULTIPLIER', 'RETRY_JITTER', 'RETRY_ON_EXCEPTIONS'
            ]
            
            missing_fields = []
            for field in retry_fields:
                if not hasattr(retry_config, field):
                    missing_fields.append(field)
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Missing retry fields: {missing_fields}")
                return
            
            # Test retry validation ranges
            validation_checks = [
                (0 <= retry_config.MAX_RETRIES <= 10, "MAX_RETRIES out of range"),
                (retry_config.INITIAL_RETRY_DELAY > 0, "INITIAL_RETRY_DELAY should be positive"),
                (retry_config.MAX_RETRY_DELAY > retry_config.INITIAL_RETRY_DELAY, "MAX_RETRY_DELAY should be greater than INITIAL_RETRY_DELAY"),
                (retry_config.RETRY_BACKOFF_MULTIPLIER >= 1.0, "RETRY_BACKOFF_MULTIPLIER should be >= 1.0"),
                (isinstance(retry_config.RETRY_ON_EXCEPTIONS, list), "RETRY_ON_EXCEPTIONS should be a list")
            ]
            
            validation_errors = []
            for check, error_msg in validation_checks:
                if not check:
                    validation_errors.append(error_msg)
            
            if validation_errors:
                self._record_test_result(test_name, False, f"Retry validation errors: {'; '.join(validation_errors)}")
                return
            
            logger.info(f"✓ Retry configuration valid - Max retries: {retry_config.MAX_RETRIES}, Backoff: {retry_config.RETRY_BACKOFF_MULTIPLIER}")
            self._record_test_result(test_name, True, "Retry configuration working correctly")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Retry configuration test failed: {str(e)}")
    
    def test_health_check_configuration(self):
        """Test health check configuration."""
        test_name = "Health Check Configuration"
        
        try:
            from config import Settings, HealthCheckConfig
            
            # Test default health check config
            health_config = HealthCheckConfig()
            
            # Check required health check fields
            health_fields = [
                'HEALTH_CHECK_INTERVAL', 'HEALTH_CHECK_TIMEOUT', 'HEALTH_CHECK_THRESHOLD',
                'HEALTH_CHECK_ENABLED', 'HEALTH_CHECK_ENDPOINT'
            ]
            
            missing_fields = []
            for field in health_fields:
                if not hasattr(health_config, field):
                    missing_fields.append(field)
            
            if missing_fields:
                self._record_test_result(test_name, False, f"Missing health check fields: {missing_fields}")
                return
            
            # Test health check validation ranges
            validation_checks = [
                (10 <= health_config.HEALTH_CHECK_INTERVAL <= 3600, "HEALTH_CHECK_INTERVAL out of range"),
                (health_config.HEALTH_CHECK_TIMEOUT > 0, "HEALTH_CHECK_TIMEOUT should be positive"),
                (health_config.HEALTH_CHECK_THRESHOLD >= 1, "HEALTH_CHECK_THRESHOLD should be >= 1"),
                (isinstance(health_config.HEALTH_CHECK_ENABLED, bool), "HEALTH_CHECK_ENABLED should be boolean"),
                (isinstance(health_config.HEALTH_CHECK_ENDPOINT, str), "HEALTH_CHECK_ENDPOINT should be string")
            ]
            
            validation_errors = []
            for check, error_msg in validation_checks:
                if not check:
                    validation_errors.append(error_msg)
            
            if validation_errors:
                self._record_test_result(test_name, False, f"Health check validation errors: {'; '.join(validation_errors)}")
                return
            
            logger.info(f"✓ Health check configuration valid - Interval: {health_config.HEALTH_CHECK_INTERVAL}s, Enabled: {health_config.HEALTH_CHECK_ENABLED}")
            self._record_test_result(test_name, True, "Health check configuration working correctly")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Health check configuration test failed: {str(e)}")
    
    def test_environment_variable_loading(self):
        """Test environment variable loading."""
        test_name = "Environment Variable Loading"
        
        try:
            from config import Settings
            
            # Test with custom environment variables
            test_env_vars = {
                'ENVIRONMENT': 'testing',
                'DEBUG': 'true',
                'PORT': '9000',
                'DOUBAO_URL': 'https://test.doubao.com',
                'LOG_LEVEL': 'DEBUG'
            }
            
            # Set environment variables
            for key, value in test_env_vars.items():
                os.environ[key] = value
            
            try:
                # Create settings with environment variables
                env_settings = Settings()
                
                # Verify environment variables were loaded
                verification_checks = [
                    (env_settings.ENVIRONMENT.value == test_env_vars['ENVIRONMENT'], 
                     f"ENVIRONMENT should be {test_env_vars['ENVIRONMENT']}"),
                    (env_settings.DEBUG == True, "DEBUG should be True"),
                    (env_settings.PORT == int(test_env_vars['PORT']), 
                     f"PORT should be {test_env_vars['PORT']}"),
                    (env_settings.DOUBAO_URL == test_env_vars['DOUBAO_URL'], 
                     f"DOUBAO_URL should be {test_env_vars['DOUBAO_URL']}"),
                    (env_settings.LOGGING.LOG_LEVEL == test_env_vars['LOG_LEVEL'], 
                     f"LOG_LEVEL should be {test_env_vars['LOG_LEVEL']}")
                ]
                
                verification_errors = []
                for check, error_msg in verification_checks:
                    if not check:
                        verification_errors.append(error_msg)
                
                if verification_errors:
                    self._record_test_result(test_name, False, f"Environment variable errors: {'; '.join(verification_errors)}")
                    return
                
                logger.info(f"✓ Environment variables loaded correctly")
                self._record_test_result(test_name, True, "Environment variable loading working correctly")
                
            finally:
                # Clean up environment variables
                for key in test_env_vars:
                    if key in os.environ:
                        del os.environ[key]
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Environment variable loading test failed: {str(e)}")
    
    def test_configuration_methods(self):
        """Test configuration methods."""
        test_name = "Configuration Methods"
        
        try:
            from config import Settings, Environment
            
            settings = Settings()
            
            # Test environment check methods
            env_methods = [
                ('is_production', lambda s: s.is_production()),
                ('is_development', lambda s: s.is_development()),
                ('is_testing', lambda s: s.is_testing())
            ]
            
            method_results = []
            for method_name, method_func in env_methods:
                try:
                    result = method_func(settings)
                    if not isinstance(result, bool):
                        method_results.append(f"{method_name} should return boolean")
                    else:
                        logger.info(f"✓ Method {method_name}() returned {result}")
                except Exception as e:
                    method_results.append(f"{method_name} failed: {str(e)}")
            
            # Test browser args method
            try:
                browser_args = settings.get_browser_args()
                if not isinstance(browser_args, list):
                    method_results.append("get_browser_args should return list")
                elif len(browser_args) == 0:
                    method_results.append("get_browser_args should not return empty list")
                else:
                    logger.info(f"✓ get_browser_args() returned {len(browser_args)} arguments")
            except Exception as e:
                method_results.append(f"get_browser_args failed: {str(e)}")
            
            # Test logging config method
            try:
                logging_config = settings.get_logging_config()
                if not isinstance(logging_config, dict):
                    method_results.append("get_logging_config should return dict")
                else:
                    logger.info(f"✓ get_logging_config() returned configuration dict")
            except Exception as e:
                method_results.append(f"get_logging_config failed: {str(e)}")
            
            if method_results:
                self._record_test_result(test_name, False, f"Configuration method errors: {'; '.join(method_results)}")
            else:
                self._record_test_result(test_name, True, "All configuration methods working correctly")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Configuration methods test failed: {str(e)}")
    
    def test_configuration_edge_cases(self):
        """Test configuration edge cases."""
        test_name = "Configuration Edge Cases"
        
        try:
            from config import Settings
            
            edge_case_tests = [
                {
                    "description": "Very long string values",
                    "settings_dict": {"PROJECT_NAME": "A" * 1000},
                    "should_work": True
                },
                {
                    "description": "Empty string values",
                    "settings_dict": {"PROJECT_NAME": ""},
                    "should_work": True
                },
                {
                    "description": "Unicode characters",
                    "settings_dict": {"PROJECT_NAME": "Doubao测试API"},
                    "should_work": True
                },
                {
                    "description": "Special characters in URL",
                    "settings_dict": {"DOUBAO_URL": "https://test.example.com/path?param=value&other=123"},
                    "should_work": True
                }
            ]
            
            edge_case_results = []
            
            for test_case in edge_case_tests:
                try:
                    settings = Settings(**test_case["settings_dict"])
                    
                    if test_case["should_work"]:
                        logger.info(f"✓ Edge case handled: {test_case['description']}")
                    else:
                        edge_case_results.append(f"{test_case['description']}: Expected failure but succeeded")
                        
                except Exception as e:
                    if test_case["should_work"]:
                        edge_case_results.append(f"{test_case['description']}: Unexpected error: {str(e)}")
                    else:
                        logger.info(f"✓ Edge case correctly failed: {test_case['description']}")
            
            if edge_case_results:
                self._record_test_result(test_name, False, f"Edge case errors: {'; '.join(edge_case_results)}")
            else:
                self._record_test_result(test_name, True, f"All edge cases handled correctly")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Configuration edge cases test failed: {str(e)}")
    
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
        logger.info("CONFIGURATION VALIDATION TEST SUMMARY")
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


def main():
    """Main test runner."""
    tester = ConfigurationTester()
    success = tester.run_all_tests()
    
    if success:
        logger.info("\n🎉 All configuration validation tests passed!")
        logger.info("The Doubao Chat API configuration system is working correctly.")
    else:
        logger.error("\n❌ Some configuration validation tests failed!")
        logger.error("Please review the configuration implementation.")
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)