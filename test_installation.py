#!/usr/bin/env python3
"""
Installation and Setup Verification Tests for Doubao Chat API

This module contains comprehensive tests to verify that the Doubao Chat API
is properly installed and configured.
"""

import os
import sys
import subprocess
import importlib
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InstallationTester:
    """Test suite for installation and setup verification."""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.project_root = Path(__file__).parent
        
    def run_all_tests(self) -> bool:
        """Run all installation verification tests."""
        logger.info("Starting installation verification tests...")
        
        # Test Python version
        self.test_python_version()
        
        # Test required files exist
        self.test_required_files()
        
        # Test dependencies installation
        self.test_dependencies()
        
        # Test environment configuration
        self.test_environment_setup()
        
        # Test imports
        self.test_imports()
        
        # Test configuration loading
        self.test_configuration()
        
        # Test Playwright setup
        self.test_playwright_setup()
        
        # Generate summary
        return self.generate_summary()
    
    def test_python_version(self):
        """Test Python version compatibility."""
        test_name = "Python Version Check"
        try:
            python_version = sys.version_info
            logger.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
            
            if python_version.major >= 3 and python_version.minor >= 8:
                self._record_test_result(test_name, True, "Python version is compatible")
            else:
                self._record_test_result(test_name, False, f"Python version {python_version.major}.{python_version.minor} is below required 3.8+")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Failed to check Python version: {str(e)}")
    
    def test_required_files(self):
        """Test that all required files exist."""
        test_name = "Required Files Check"
        required_files = [
            "requirements.txt",
            "main.py", 
            "config.py",
            "doubao_automation.py",
            "middleware.py",
            "test_selectors.py"
        ]
        
        try:
            missing_files = []
            for file_name in required_files:
                file_path = self.project_root / file_name
                if not file_path.exists():
                    missing_files.append(file_name)
                else:
                    logger.info(f"✓ Found required file: {file_name}")
            
            if missing_files:
                self._record_test_result(test_name, False, f"Missing required files: {', '.join(missing_files)}")
            else:
                self._record_test_result(test_name, True, "All required files found")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Failed to check required files: {str(e)}")
    
    def test_dependencies(self):
        """Test that all dependencies are properly installed."""
        test_name = "Dependencies Check"
        
        try:
            # Read requirements.txt
            requirements_path = self.project_root / "requirements.txt"
            if not requirements_path.exists():
                self._record_test_result(test_name, False, "requirements.txt not found")
                return
            
            with open(requirements_path, 'r') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            missing_deps = []
            installed_deps = []
            
            for req in requirements:
                # Extract package name (remove version specifiers)
                package_name = req.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
                
                try:
                    importlib.import_module(package_name.replace('-', '_').replace('.', '_'))
                    installed_deps.append(package_name)
                    logger.info(f"✓ Installed: {package_name}")
                except ImportError:
                    missing_deps.append(package_name)
                    logger.warning(f"✗ Missing: {package_name}")
            
            if missing_deps:
                self._record_test_result(test_name, False, f"Missing dependencies: {', '.join(missing_deps)}")
            else:
                self._record_test_result(test_name, True, f"All {len(installed_deps)} dependencies installed")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Failed to check dependencies: {str(e)}")
    
    def test_environment_setup(self):
        """Test environment setup and variables."""
        test_name = "Environment Setup Check"
        
        try:
            # Check if .env file exists (optional but recommended)
            env_file = self.project_root / ".env"
            if env_file.exists():
                logger.info("✓ .env file found")
            else:
                logger.warning("⚠ .env file not found (optional but recommended)")
            
            # Check environment variables
            required_env_vars = []
            optional_env_vars = ['DOUBAO_URL', 'DOUBAO_USERNAME', 'DOUBAO_PASSWORD']
            
            missing_required = []
            for var in required_env_vars:
                if var not in os.environ:
                    missing_required.append(var)
            
            present_optional = []
            for var in optional_env_vars:
                if var in os.environ:
                    present_optional.append(var)
                    logger.info(f"✓ Environment variable set: {var}")
            
            if missing_required:
                self._record_test_result(test_name, False, f"Missing required environment variables: {', '.join(missing_required)}")
            else:
                status_msg = "Environment setup OK"
                if present_optional:
                    status_msg += f" (optional vars: {', '.join(present_optional)})"
                self._record_test_result(test_name, True, status_msg)
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Failed to check environment setup: {str(e)}")
    
    def test_imports(self):
        """Test that all modules can be imported successfully."""
        test_name = "Module Imports Check"
        
        try:
            modules_to_test = [
                'config',
                'main',
                'doubao_automation',
                'middleware',
                'test_selectors'
            ]
            
            import_errors = []
            successful_imports = []
            
            for module_name in modules_to_test:
                try:
                    module = importlib.import_module(module_name)
                    successful_imports.append(module_name)
                    logger.info(f"✓ Successfully imported: {module_name}")
                except Exception as e:
                    import_errors.append(f"{module_name}: {str(e)}")
                    logger.error(f"✗ Failed to import {module_name}: {str(e)}")
            
            if import_errors:
                self._record_test_result(test_name, False, f"Import errors: {'; '.join(import_errors)}")
            else:
                self._record_test_result(test_name, True, f"All {len(successful_imports)} modules imported successfully")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Failed to test imports: {str(e)}")
    
    def test_configuration(self):
        """Test configuration loading and validation."""
        test_name = "Configuration Check"
        
        try:
            from config import settings, Settings
            
            # Test settings object creation
            test_settings = Settings()
            logger.info(f"✓ Settings loaded successfully")
            logger.info(f"  Environment: {test_settings.ENVIRONMENT.value}")
            logger.info(f"  Debug mode: {test_settings.DEBUG}")
            logger.info(f"  Port: {test_settings.PORT}")
            logger.info(f"  Doubao URL: {test_settings.DOUBAO_URL}")
            
            # Test validation methods
            validation_tests = [
                test_settings.is_production(),
                test_settings.is_development(),
                test_settings.is_testing()
            ]
            logger.info(f"✓ Configuration validation methods work")
            
            # Test browser args generation
            browser_args = test_settings.get_browser_args()
            logger.info(f"✓ Browser arguments generated: {len(browser_args)} args")
            
            # Test logging config
            logging_config = test_settings.get_logging_config()
            logger.info(f"✓ Logging configuration generated")
            
            self._record_test_result(test_name, True, "Configuration loaded and validated successfully")
            
        except Exception as e:
            self._record_test_result(test_name, False, f"Configuration error: {str(e)}")
    
    def test_playwright_setup(self):
        """Test Playwright browser setup."""
        test_name = "Playwright Setup Check"
        
        try:
            # Test Playwright import
            import playwright
            logger.info(f"✓ Playwright version: {playwright.__version__}")
            
            # Test if browsers are installed
            try:
                result = subprocess.run(['playwright', 'install', '--dry-run'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("✓ Playwright browsers are properly installed")
                    self._record_test_result(test_name, True, "Playwright setup OK")
                else:
                    logger.warning(f"⚠ Playwright browser installation needed: {result.stderr}")
                    self._record_test_result(test_name, False, "Playwright browsers need to be installed")
            except subprocess.TimeoutExpired:
                self._record_test_result(test_name, False, "Playwright check timed out")
            except FileNotFoundError:
                self._record_test_result(test_name, False, "Playwright CLI not found")
                
        except ImportError as e:
            self._record_test_result(test_name, False, f"Playwright not installed: {str(e)}")
        except Exception as e:
            self._record_test_result(test_name, False, f"Playwright setup error: {str(e)}")
    
    def _record_test_result(self, test_name: str, passed: bool, message: str):
        """Record a test result."""
        result = {
            'test_name': test_name,
            'passed': passed,
            'message': message,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{status}: {test_name} - {message}")
    
    def generate_summary(self) -> bool:
        """Generate test summary and return overall success status."""
        logger.info("\n" + "="*60)
        logger.info("INSTALLATION VERIFICATION SUMMARY")
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
    tester = InstallationTester()
    success = tester.run_all_tests()
    
    if success:
        logger.info("\n🎉 All installation verification tests passed!")
        logger.info("The Doubao Chat API is properly installed and configured.")
    else:
        logger.error("\n❌ Some installation verification tests failed!")
        logger.error("Please address the issues above before proceeding.")
    
    return 0 if success else 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)