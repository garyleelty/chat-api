#!/usr/bin/env python3
"""
Performance and Load Testing Basics for Doubao Chat API

This module contains basic performance and load testing functionality
to verify the API can handle expected traffic and perform efficiently.
"""

import asyncio
import httpx
import logging
import time
import statistics
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceTester:
    """Basic performance and load testing suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.test_results: List[Dict[str, Any]] = []
        self.client = None
        
    async def setup(self):
        """Setup test client."""
        self.client = httpx.AsyncClient(timeout=60.0)  # Longer timeout for performance tests
        
    async def teardown(self):
        """Cleanup test client."""
        if self.client:
            await self.client.aclose()
    
    async def run_all_tests(self) -> bool:
        """Run all performance and load tests."""
        logger.info("Starting performance and load tests...")
        
        await self.setup()
        
        try:
            # Test response time benchmarks
            await self.test_response_time_benchmarks()
            
            # Test concurrent user simulation
            await self.test_concurrent_users()
            
            # Test sustained load
            await self.test_sustained_load()
            
            # Test memory usage patterns
            await self.test_memory_usage_patterns()
            
            # Test throughput capacity
            await self.test_throughput_capacity()
            
            # Test latency under load
            await self.test_latency_under_load()
            
            # Test resource utilization
            await self.test_resource_utilization()
            
            # Test scalability limits
            await self.test_scalability_limits()
            
            # Generate summary
            return self.generate_summary()
            
        finally:
            await self.teardown()
    
    async def test_response_time_benchmarks(self):
        """Test response time benchmarks."""
        test_name = "Response Time Benchmarks"
        
        try:
            # Test different endpoint response times
            endpoints = [
                {"name": "Root endpoint", "url": f"{self.base_url}/", "method": "GET"},
                {"name": "Health check", "url": f"{self.base_url}/health", "method": "GET"},
                {"name": "Chat endpoint", "url": f"{self.base_url}/chat", "method": "POST", "payload": {"message": "Performance test message"}}
            ]
            
            response_times = {}
            
            for endpoint in endpoints:
                times = []
                
                # Make 10 requests to each endpoint
                for i in range(10):
                    start_time = time.time()
                    
                    try:
                        if endpoint["method"] == "GET":
                            response = await self.client.get(endpoint["url"])
                        else:
                            response = await self.client.post(endpoint["url"], json=endpoint.get("payload", {}))
                        
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                        
                        if response.status_code == 200:
                            times.append(response_time)
                        else:
                            logger.warning(f"Endpoint {endpoint['name']} request {i} failed: {response.status_code}")
                            
                    except Exception as e:
                        logger.warning(f"Endpoint {endpoint['name']} request {i} error: {str(e)}")
                
                if times:
                    avg_time = statistics.mean(times)
                    median_time = statistics.median(times)
                    p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
                    
                    response_times[endpoint["name"]] = {
                        "avg_ms": avg_time,
                        "median_ms": median_time,
                        "p95_ms": p95_time,
                        "samples": len(times)
                    }
                    
                    logger.info(f"✓ {endpoint['name']} - Avg: {avg_time:.2f}ms, P95: {p95_time:.2f}ms")
                else:
                    response_times[endpoint["name"]] = {"error": "No successful requests"}
            
            # Analyze results
            chat_times = response_times.get("Chat endpoint", {})
            if "avg_ms" in chat_times:
                avg_chat_time = chat_times["avg_ms"]
                
                if avg_chat_time < 1000:  # Less than 1 second
                    performance_rating = "Excellent"
                elif avg_chat_time < 3000:  # Less than 3 seconds
                    performance_rating = "Good"
                elif avg_chat_time < 10000:  # Less than 10 seconds
                    performance_rating = "Acceptable"
                else:
                    performance_rating = "Poor"
                
                self._record_test_result(test_name, True, 
                    f"Response times {performance_rating.lower()} - Chat avg: {avg_chat_time:.2f}ms, P95: {chat_times.get('p95_ms', 0):.2f}ms")
            else:
                self._record_test_result(test_name, False, "Could not measure chat endpoint response times")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Response time benchmark test failed: {str(e)}")
    
    async def test_concurrent_users(self):
        """Test concurrent user simulation."""
        test_name = "Concurrent Users"
        
        try:
            concurrent_levels = [5, 10, 20]  # Test with different concurrency levels
            user_results = []
            
            for concurrent_users in concurrent_levels:
                logger.info(f"Testing with {concurrent_users} concurrent users...")
                
                async def simulate_user(user_id: int) -> Dict[str, Any]:
                    start_time = time.time()
                    
                    try:
                        payload = {"message": f"Concurrent test message from user {user_id}"}
                        response = await self.client.post(f"{self.base_url}/chat", json=payload)
                        
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        return {
                            "user_id": user_id,
                            "success": response.status_code == 200,
                            "response_time_ms": response_time,
                            "status_code": response.status_code
                        }
                        
                    except Exception as e:
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        return {
                            "user_id": user_id,
                            "success": False,
                            "response_time_ms": response_time,
                            "error": str(e)
                        }
                
                # Create concurrent tasks
                tasks = [simulate_user(i) for i in range(concurrent_users)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Analyze results for this concurrency level
                successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
                failed_requests = concurrent_users - successful_requests
                
                if successful_requests > 0:
                    successful_times = [r['response_time_ms'] for r in results if isinstance(r, dict) and r.get('success', False)]
                    avg_response_time = statistics.mean(successful_times)
                    
                    user_results.append({
                        "concurrent_users": concurrent_users,
                        "success_rate": successful_requests / concurrent_users,
                        "avg_response_time_ms": avg_response_time,
                        "failed_requests": failed_requests
                    })
                    
                    logger.info(f"✓ {concurrent_users} users - Success rate: {successful_requests/concurrent_users:.1%}, Avg time: {avg_response_time:.2f}ms")
                else:
                    user_results.append({
                        "concurrent_users": concurrent_users,
                        "success_rate": 0,
                        "failed_requests": failed_requests
                    })
                    logger.warning(f"✗ {concurrent_users} users - All requests failed")
            
            # Overall analysis
            if user_results:
                best_result = max(user_results, key=lambda x: x['success_rate'])
                worst_result = min(user_results, key=lambda x: x['success_rate'])
                
                if best_result['success_rate'] >= 0.8:  # 80% success rate
                    self._record_test_result(test_name, True, 
                        f"Concurrent users OK - Best: {best_result['concurrent_users']} users at {best_result['success_rate']:.1%} success rate")
                else:
                    self._record_test_result(test_name, False, 
                        f"Concurrent users performance poor - Best success rate: {best_result['success_rate']:.1%}")
            else:
                self._record_test_result(test_name, False, "No concurrent user test results")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Concurrent users test failed: {str(e)}")
    
    async def test_sustained_load(self):
        """Test sustained load over time."""
        test_name = "Sustained Load"
        
        try:
            duration_seconds = 30  # Test for 30 seconds
            requests_per_second = 2  # 2 requests per second
            
            logger.info(f"Testing sustained load: {requests_per_second} req/s for {duration_seconds} seconds...")
            
            start_time = time.time()
            end_time = start_time + duration_seconds
            request_times = []
            successful_requests = 0
            failed_requests = 0
            
            while time.time() < end_time:
                batch_start = time.time()
                
                # Send a batch of requests
                batch_tasks = []
                for i in range(requests_per_second):
                    task = self.client.post(f"{self.base_url}/chat", json={"message": f"Sustained load test {i}"})
                    batch_tasks.append(task)
                
                try:
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    for result in batch_results:
                        if isinstance(result, httpx.Response):
                            if result.status_code == 200:
                                successful_requests += 1
                            else:
                                failed_requests += 1
                        else:
                            failed_requests += 1
                    
                except Exception as e:
                    failed_requests += requests_per_second
                    logger.warning(f"Batch error: {str(e)}")
                
                # Wait to maintain request rate
                batch_duration = time.time() - batch_start
                wait_time = max(0, 1.0 - batch_duration)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            total_requests = successful_requests + failed_requests
            success_rate = successful_requests / total_requests if total_requests > 0 else 0
            actual_duration = time.time() - start_time
            actual_rps = total_requests / actual_duration
            
            logger.info(f"Sustained load results - Total: {total_requests}, Success: {successful_requests}, RPS: {actual_rps:.2f}")
            
            if success_rate >= 0.9 and actual_rps >= requests_per_second * 0.8:  # 90% success, 80% of target RPS
                self._record_test_result(test_name, True, 
                    f"Sustained load OK - {success_rate:.1%} success rate, {actual_rps:.2f} RPS")
            else:
                self._record_test_result(test_name, False, 
                    f"Sustained load issues - Success rate: {success_rate:.1%}, RPS: {actual_rps:.2f}")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Sustained load test failed: {str(e)}")
    
    async def test_memory_usage_patterns(self):
        """Test memory usage patterns under load."""
        test_name = "Memory Usage Patterns"
        
        try:
            # This is a basic test since we can't directly measure server memory
            # We'll infer memory issues from response patterns and error rates
            
            logger.info("Testing memory usage patterns...")
            
            # Send a series of requests and monitor for degradation
            request_batches = 5
            requests_per_batch = 10
            batch_results = []
            
            for batch in range(request_batches):
                batch_start_time = time.time()
                batch_successes = 0
                batch_failures = 0
                batch_times = []
                
                for req in range(requests_per_batch):
                    try:
                        start_time = time.time()
                        response = await self.client.post(
                            f"{self.base_url}/chat", 
                            json={"message": f"Memory test batch {batch} request {req}"}
                        )
                        end_time = time.time()
                        
                        response_time = (end_time - start_time) * 1000
                        batch_times.append(response_time)
                        
                        if response.status_code == 200:
                            batch_successes += 1
                        else:
                            batch_failures += 1
                            
                    except Exception as e:
                        batch_failures += 1
                        logger.debug(f"Request {req} in batch {batch} failed: {str(e)}")
                
                batch_duration = time.time() - batch_start_time
                
                batch_results.append({
                    "batch": batch,
                    "successes": batch_successes,
                    "failures": batch_failures,
                    "avg_response_time": statistics.mean(batch_times) if batch_times else 0,
                    "duration": batch_duration
                })
                
                logger.info(f"Batch {batch} - Successes: {batch_successes}, Failures: {batch_failures}, Avg time: {batch_results[-1]['avg_response_time']:.2f}ms")
                
                # Small delay between batches
                await asyncio.sleep(1)
            
            # Analyze for memory-related degradation
            success_rates = [r['successes'] / (r['successes'] + r['failures']) for r in batch_results]
            response_times = [r['avg_response_time'] for r in batch_results]
            
            # Check for degradation trends
            success_trend = success_rates[-1] - success_rates[0]  # Should not decrease significantly
            time_trend = response_times[-1] - response_times[0]  # Should not increase significantly
            
            logger.info(f"Memory pattern analysis - Success trend: {success_trend:+.3f}, Time trend: {time_trend:+.2f}ms")
            
            if success_trend >= -0.1 and time_trend <= 1000:  # Max 10% success drop, 1s time increase
                self._record_test_result(test_name, True, 
                    f"Memory usage patterns OK - Success trend: {success_trend:+.3f}, Time trend: {time_trend:+.2f}ms")
            else:
                self._record_test_result(test_name, False, 
                    f"Memory usage degradation detected - Success trend: {success_trend:+.3f}, Time trend: {time_trend:+.2f}ms")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Memory usage patterns test failed: {str(e)}")
    
    async def test_throughput_capacity(self):
        """Test throughput capacity."""
        test_name = "Throughput Capacity"
        
        try:
            # Test maximum sustainable throughput
            logger.info("Testing throughput capacity...")
            
            # Start with a moderate load and increase gradually
            throughput_levels = [1, 2, 5, 10]  # Requests per second
            throughput_results = []
            
            for target_rps in throughput_levels:
                logger.info(f"Testing throughput at {target_rps} RPS...")
                
                test_duration = 10  # 10 seconds per level
                start_time = time.time()
                end_time = start_time + test_duration
                
                total_requests = 0
                successful_requests = 0
                
                while time.time() < end_time:
                    batch_start = time.time()
                    
                    # Send batch of requests
                    batch_size = target_rps
                    batch_tasks = []
                    
                    for i in range(batch_size):
                        task = self.client.post(
                            f"{self.base_url}/chat", 
                            json={"message": f"Throughput test at {target_rps} RPS"}
                        )
                        batch_tasks.append(task)
                    
                    try:
                        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                        
                        for result in batch_results:
                            total_requests += 1
                            if isinstance(result, httpx.Response) and result.status_code == 200:
                                successful_requests += 1
                        
                    except Exception as e:
                        total_requests += batch_size
                        logger.debug(f"Batch error at {target_rps} RPS: {str(e)}")
                    
                    # Maintain target rate
                    batch_duration = time.time() - batch_start
                    wait_time = max(0, 1.0 - batch_duration)
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                
                actual_duration = time.time() - start_time
                actual_rps = total_requests / actual_duration
                success_rate = successful_requests / total_requests if total_requests > 0 else 0
                
                throughput_results.append({
                    "target_rps": target_rps,
                    "actual_rps": actual_rps,
                    "success_rate": success_rate,
                    "total_requests": total_requests,
                    "successful_requests": successful_requests
                })
                
                logger.info(f"✓ {target_rps} RPS target - Actual: {actual_rps:.2f} RPS, Success: {success_rate:.1%}")
                
                # If success rate drops below 80%, stop increasing load
                if success_rate < 0.8:
                    logger.info(f"Stopping throughput test - success rate dropped to {success_rate:.1%}")
                    break
            
            # Find maximum sustainable throughput
            if throughput_results:
                sustainable_results = [r for r in throughput_results if r['success_rate'] >= 0.8]
                
                if sustainable_results:
                    max_sustainable = max(sustainable_results, key=lambda x: x['actual_rps'])
                    self._record_test_result(test_name, True, 
                        f"Throughput capacity OK - Max sustainable: {max_sustainable['actual_rps']:.2f} RPS at {max_sustainable['success_rate']:.1%} success rate")
                else:
                    self._record_test_result(test_name, False, 
                        "No sustainable throughput level found - all levels had <80% success rate")
            else:
                self._record_test_result(test_name, False, "No throughput test results")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Throughput capacity test failed: {str(e)}")
    
    async def test_latency_under_load(self):
        """Test latency under different load conditions."""
        test_name = "Latency Under Load"
        
        try:
            logger.info("Testing latency under load...")
            
            # Test latency at different load levels
            load_levels = [1, 5, 10]  # Concurrent requests
            latency_results = []
            
            for concurrent_load in load_levels:
                logger.info(f"Testing latency with {concurrent_load} concurrent requests...")
                
                async def measure_latency(request_id: int) -> float:
                    start_time = time.time()
                    
                    try:
                        response = await self.client.post(
                            f"{self.base_url}/chat", 
                            json={"message": f"Latency test request {request_id}"}
                        )
                        
                        end_time = time.time()
                        latency = (end_time - start_time) * 1000  # Convert to milliseconds
                        
                        if response.status_code == 200:
                            return latency
                        else:
                            return -1  # Indicate failure
                            
                    except Exception:
                        return -1  # Indicate failure
                
                # Create concurrent latency measurement tasks
                tasks = [measure_latency(i) for i in range(concurrent_load * 2)]  # 2 requests per concurrent user
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Analyze latency results
                successful_latencies = [r for r in results if isinstance(r, (int, float)) and r > 0]
                failed_requests = len(results) - len(successful_latencies)
                
                if successful_latencies:
                    avg_latency = statistics.mean(successful_latencies)
                    median_latency = statistics.median(successful_latencies)
                    p95_latency = sorted(successful_latencies)[int(len(successful_latencies) * 0.95)] if len(successful_latencies) > 1 else successful_latencies[0]
                    
                    latency_results.append({
                        "concurrent_load": concurrent_load,
                        "avg_latency_ms": avg_latency,
                        "median_latency_ms": median_latency,
                        "p95_latency_ms": p95_latency,
                        "failed_requests": failed_requests,
                        "success_rate": len(successful_latencies) / len(results)
                    })
                    
                    logger.info(f"✓ {concurrent_load} concurrent - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms, Success: {latency_results[-1]['success_rate']:.1%}")
                else:
                    latency_results.append({
                        "concurrent_load": concurrent_load,
                        "failed_requests": failed_requests,
                        "success_rate": 0
                    })
                    logger.warning(f"✗ {concurrent_load} concurrent - All requests failed")
            
            # Analyze latency scaling
            if len(latency_results) >= 2:
                first_result = latency_results[0]
                last_result = latency_results[-1]
                
                if first_result.get('avg_latency_ms') and last_result.get('avg_latency_ms'):
                    latency_increase = last_result['avg_latency_ms'] - first_result['avg_latency_ms']
                    load_increase = last_result['concurrent_load'] - first_result['concurrent_load']
                    
                    if load_increase > 0:
                        latency_per_load = latency_increase / load_increase
                        
                        logger.info(f"Latency scaling - Increase: {latency_increase:.2f}ms for {load_increase} additional concurrent users")
                        
                        if latency_per_load < 500:  # Less than 500ms increase per additional user
                            self._record_test_result(test_name, True, 
                                f"Latency scaling OK - {latency_per_load:.2f}ms increase per additional user")
                        else:
                            self._record_test_result(test_name, False, 
                                f"Latency scaling poor - {latency_per_load:.2f}ms increase per additional user")
                    else:
                        self._record_test_result(test_name, True, "Latency under load stable")
                else:
                    self._record_test_result(test_name, False, "Could not measure latency scaling")
            else:
                self._record_test_result(test_name, False, "Insufficient latency test data")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Latency under load test failed: {str(e)}")
    
    async def test_resource_utilization(self):
        """Test resource utilization patterns."""
        test_name = "Resource Utilization"
        
        try:
            logger.info("Testing resource utilization patterns...")
            
            # Monitor API behavior under different loads to infer resource usage
            utilization_tests = [
                {"name": "Light load", "concurrent": 2, "duration": 10},
                {"name": "Medium load", "concurrent": 5, "duration": 10},
                {"name": "Heavy load", "concurrent": 10, "duration": 10}
            ]
            
            utilization_results = []
            
            for test_config in utilization_tests:
                logger.info(f"Testing {test_config['name']} - {test_config['concurrent']} concurrent for {test_config['duration']}s...")
                
                start_time = time.time()
                end_time = start_time + test_config['duration']
                
                total_requests = 0
                successful_requests = 0
                response_times = []
                error_count = 0
                
                while time.time() < end_time:
                    # Send concurrent requests
                    batch_tasks = []
                    for i in range(test_config['concurrent']):
                        task = self.client.post(
                            f"{self.base_url}/chat", 
                            json={"message": f"Resource test {test_config['name']} request {i}"}
                        )
                        batch_tasks.append(task)
                    
                    try:
                        batch_start = time.time()
                        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                        batch_time = time.time() - batch_start
                        
                        for result in batch_results:
                            total_requests += 1
                            
                            if isinstance(result, httpx.Response):
                                if result.status_code == 200:
                                    successful_requests += 1
                                    response_times.append(batch_time * 1000 / test_config['concurrent'])  # Approximate per-request time
                                else:
                                    error_count += 1
                            else:
                                error_count += 1
                        
                    except Exception as e:
                        error_count += test_config['concurrent']
                        logger.debug(f"Batch error in {test_config['name']}: {str(e)}")
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.5)
                
                actual_duration = time.time() - start_time
                rps = total_requests / actual_duration
                success_rate = successful_requests / total_requests if total_requests > 0 else 0
                avg_response_time = statistics.mean(response_times) if response_times else 0
                
                utilization_results.append({
                    "test_name": test_config['name'],
                    "concurrent": test_config['concurrent'],
                    "rps": rps,
                    "success_rate": success_rate,
                    "avg_response_time_ms": avg_response_time,
                    "error_count": error_count,
                    "total_requests": total_requests
                })
                
                logger.info(f"✓ {test_config['name']} - RPS: {rps:.2f}, Success: {success_rate:.1%}, Avg time: {avg_response_time:.2f}ms")
            
            # Analyze resource utilization efficiency
            if utilization_results:
                # Look for signs of resource exhaustion
                efficiency_decline = False
                resource_warnings = []
                
                for i in range(1, len(utilization_results)):
                    prev = utilization_results[i-1]
                    curr = utilization_results[i]
                    
                    # Check for significant performance degradation
                    success_drop = prev['success_rate'] - curr['success_rate']
                    time_increase = curr['avg_response_time_ms'] - prev['avg_response_time_ms']
                    
                    if success_drop > 0.2:  # More than 20% success rate drop
                        efficiency_decline = True
                        resource_warnings.append(f"{curr['test_name']} has {success_drop:.1%} success rate drop")
                    
                    if time_increase > 2000:  # More than 2s response time increase
                        efficiency_decline = True
                        resource_warnings.append(f"{curr['test_name']} has {time_increase:.0f}ms response time increase")
                
                if efficiency_decline:
                    self._record_test_result(test_name, False, 
                        f"Resource utilization issues - {', '.join(resource_warnings)}")
                else:
                    best_result = max(utilization_results, key=lambda x: x['rps'] * x['success_rate'])
                    self._record_test_result(test_name, True, 
                        f"Resource utilization OK - Best efficiency: {best_result['test_name']} at {best_result['rps']:.2f} RPS")
            else:
                self._record_test_result(test_name, False, "No resource utilization results")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Resource utilization test failed: {str(e)}")
    
    async def test_scalability_limits(self):
        """Test scalability limits."""
        test_name = "Scalability Limits"
        
        try:
            logger.info("Testing scalability limits...")
            
            # Find the breaking point by gradually increasing load
            max_concurrent = 50  # Maximum to test
            step_size = 5
            
            scalability_results = []
            breaking_point = None
            
            for concurrent_users in range(step_size, max_concurrent + step_size, step_size):
                logger.info(f"Testing scalability at {concurrent_users} concurrent users...")
                
                async def single_request(user_id: int) -> bool:
                    try:
                        response = await self.client.post(
                            f"{self.base_url}/chat", 
                            json={"message": f"Scalability test user {user_id}"}
                        )
                        return response.status_code == 200
                    except Exception:
                        return False
                
                # Send concurrent requests
                tasks = [single_request(i) for i in range(concurrent_users)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                successful_requests = sum(1 for r in results if r is True)
                success_rate = successful_requests / concurrent_users
                
                scalability_results.append({
                    "concurrent_users": concurrent_users,
                    "success_rate": success_rate,
                    "successful_requests": successful_requests
                })
                
                logger.info(f"✓ {concurrent_users} users - Success rate: {success_rate:.1%}")
                
                # If success rate drops below 50%, we've found the breaking point
                if success_rate < 0.5 and breaking_point is None:
                    breaking_point = concurrent_users
                    logger.info(f"Breaking point found at {concurrent_users} concurrent users")
                    break
                
                # If we're at max_concurrent and still doing well, that's great
                if concurrent_users >= max_concurrent and success_rate >= 0.8:
                    breaking_point = max_concurrent
                    logger.info(f"System handles {max_concurrent} concurrent users excellently")
                    break
            
            # Analyze scalability
            if scalability_results:
                if breaking_point:
                    if breaking_point >= 20:  # Can handle at least 20 concurrent users
                        self._record_test_result(test_name, True, 
                            f"Scalability good - Handles up to {breaking_point} concurrent users")
                    elif breaking_point >= 10:
                        self._record_test_result(test_name, True, 
                            f"Scalability acceptable - Handles up to {breaking_point} concurrent users")
                    else:
                        self._record_test_result(test_name, False, 
                            f"Scalability limited - Breaking point at {breaking_point} concurrent users")
                else:
                    max_tested = max(r['concurrent_users'] for r in scalability_results)
                    self._record_test_result(test_name, True, 
                        f"Scalability excellent - Tested up to {max_tested} concurrent users")
            else:
                self._record_test_result(test_name, False, "No scalability test results")
                
        except Exception as e:
            self._record_test_result(test_name, False, f"Scalability limits test failed: {str(e)}")
    
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
        logger.info("PERFORMANCE AND LOAD TEST SUMMARY")
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
    
    tester = PerformanceTester(base_url)
    success = await tester.run_all_tests()
    
    if success:
        logger.info("\n🎉 All performance and load tests passed!")
        logger.info("The Doubao Chat API demonstrates good performance characteristics.")
    else:
        logger.error("\n❌ Some performance and load tests failed!")
        logger.error("Please review performance bottlenecks and optimization opportunities.")
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)