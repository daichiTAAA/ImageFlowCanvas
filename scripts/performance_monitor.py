#!/usr/bin/env python3

"""
Performance monitoring script for ImageFlowCanvas gRPC services
Measures processing times and validates 1-3 second target performance
"""

import time
import json
import logging
import asyncio
import statistics
from typing import List, Dict, Any
from datetime import datetime

import requests
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self, gateway_url="http://localhost:8080"):
        self.gateway_url = gateway_url
        self.results = []
        
    def create_test_payload(self, test_id: str = None) -> Dict[str, Any]:
        """Create test payload for performance testing"""
        if test_id is None:
            test_id = f"perf-test-{int(time.time())}"
            
        return {
            "input_image": {
                "bucket": "test-bucket",
                "object_key": "test-image.jpg",
                "content_type": "image/jpeg"
            },
            "execution_id": test_id
        }
    
    def measure_resize_performance(self, iterations: int = 10) -> Dict[str, Any]:
        """Measure resize service performance"""
        logger.info(f"Testing resize service performance ({iterations} iterations)")
        times = []
        
        for i in range(iterations):
            payload = self.create_test_payload(f"resize-test-{i}")
            payload.update({
                "target_width": 800,
                "target_height": 600,
                "maintain_aspect_ratio": True,
                "quality": "RESIZE_QUALITY_GOOD"
            })
            
            start_time = time.time()
            try:
                response = requests.post(
                    f"{self.gateway_url}/v1/resize",
                    json=payload,
                    timeout=30
                )
                
                processing_time = time.time() - start_time
                times.append(processing_time)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Resize iteration {i+1}: {processing_time:.2f}s - {result.get('result', {}).get('message', 'OK')}")
                else:
                    logger.warning(f"Resize iteration {i+1}: Failed with status {response.status_code}")
                    
            except Exception as e:
                processing_time = time.time() - start_time
                times.append(processing_time)
                logger.error(f"Resize iteration {i+1}: Error - {e}")
            
            time.sleep(0.5)  # Brief pause between tests
        
        return self._calculate_stats("resize", times)
    
    def measure_detection_performance(self, iterations: int = 5) -> Dict[str, Any]:
        """Measure AI detection service performance"""
        logger.info(f"Testing AI detection service performance ({iterations} iterations)")
        times = []
        
        for i in range(iterations):
            payload = self.create_test_payload(f"detection-test-{i}")
            payload.update({
                "model_name": "yolo",
                "confidence_threshold": 0.5,
                "nms_threshold": 0.4,
                "draw_boxes": True
            })
            
            start_time = time.time()
            try:
                response = requests.post(
                    f"{self.gateway_url}/v1/detect",
                    json=payload,
                    timeout=60
                )
                
                processing_time = time.time() - start_time
                times.append(processing_time)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Detection iteration {i+1}: {processing_time:.2f}s - {result.get('result', {}).get('message', 'OK')}")
                else:
                    logger.warning(f"Detection iteration {i+1}: Failed with status {response.status_code}")
                    
            except Exception as e:
                processing_time = time.time() - start_time
                times.append(processing_time)
                logger.error(f"Detection iteration {i+1}: Error - {e}")
            
            time.sleep(1.0)  # Longer pause for AI processing
        
        return self._calculate_stats("detection", times)
    
    def measure_filter_performance(self, iterations: int = 10) -> Dict[str, Any]:
        """Measure filter service performance"""
        logger.info(f"Testing filter service performance ({iterations} iterations)")
        times = []
        
        for i in range(iterations):
            payload = self.create_test_payload(f"filter-test-{i}")
            payload.update({
                "filter_type": "FILTER_TYPE_BLUR",
                "intensity": 1.0,
                "parameters": {}
            })
            
            start_time = time.time()
            try:
                response = requests.post(
                    f"{self.gateway_url}/v1/filter",
                    json=payload,
                    timeout=30
                )
                
                processing_time = time.time() - start_time
                times.append(processing_time)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Filter iteration {i+1}: {processing_time:.2f}s - {result.get('result', {}).get('message', 'OK')}")
                else:
                    logger.warning(f"Filter iteration {i+1}: Failed with status {response.status_code}")
                    
            except Exception as e:
                processing_time = time.time() - start_time
                times.append(processing_time)
                logger.error(f"Filter iteration {i+1}: Error - {e}")
            
            time.sleep(0.5)  # Brief pause between tests
        
        return self._calculate_stats("filter", times)
    
    def measure_pipeline_performance(self, iterations: int = 5) -> Dict[str, Any]:
        """Measure full pipeline performance (resize -> detection -> filter)"""
        logger.info(f"Testing full pipeline performance ({iterations} iterations)")
        times = []
        
        for i in range(iterations):
            base_payload = self.create_test_payload(f"pipeline-test-{i}")
            
            start_time = time.time()
            try:
                # Step 1: Resize
                resize_payload = {**base_payload}
                resize_payload.update({
                    "target_width": 800,
                    "target_height": 600,
                    "maintain_aspect_ratio": True,
                    "quality": "RESIZE_QUALITY_GOOD"
                })
                
                resize_response = requests.post(
                    f"{self.gateway_url}/v1/resize",
                    json=resize_payload,
                    timeout=30
                )
                
                if resize_response.status_code != 200:
                    raise Exception(f"Resize failed: {resize_response.status_code}")
                
                # Step 2: Detection (using resized image)
                detection_payload = {**base_payload}
                detection_payload["input_image"]["object_key"] = resize_response.json()["result"]["output_image"]["object_key"]
                detection_payload.update({
                    "model_name": "yolo",
                    "confidence_threshold": 0.5,
                    "nms_threshold": 0.4,
                    "draw_boxes": True
                })
                
                detection_response = requests.post(
                    f"{self.gateway_url}/v1/detect",
                    json=detection_payload,
                    timeout=60
                )
                
                if detection_response.status_code != 200:
                    raise Exception(f"Detection failed: {detection_response.status_code}")
                
                # Step 3: Filter (using detected image)
                filter_payload = {**base_payload}
                filter_payload["input_image"]["object_key"] = detection_response.json()["result"]["output_image"]["object_key"]
                filter_payload.update({
                    "filter_type": "FILTER_TYPE_BLUR",
                    "intensity": 1.0,
                    "parameters": {}
                })
                
                filter_response = requests.post(
                    f"{self.gateway_url}/v1/filter",
                    json=filter_payload,
                    timeout=30
                )
                
                if filter_response.status_code != 200:
                    raise Exception(f"Filter failed: {filter_response.status_code}")
                
                total_time = time.time() - start_time
                times.append(total_time)
                
                logger.info(f"Pipeline iteration {i+1}: {total_time:.2f}s")
                
            except Exception as e:
                total_time = time.time() - start_time
                times.append(total_time)
                logger.error(f"Pipeline iteration {i+1}: Error - {e}")
            
            time.sleep(2.0)  # Longer pause for full pipeline
        
        return self._calculate_stats("pipeline", times)
    
    def _calculate_stats(self, service_name: str, times: List[float]) -> Dict[str, Any]:
        """Calculate performance statistics"""
        if not times:
            return {
                "service": service_name,
                "error": "No valid measurements"
            }
        
        valid_times = [t for t in times if t > 0]
        
        stats = {
            "service": service_name,
            "iterations": len(times),
            "valid_measurements": len(valid_times),
            "min_time": min(valid_times) if valid_times else 0,
            "max_time": max(valid_times) if valid_times else 0,
            "avg_time": statistics.mean(valid_times) if valid_times else 0,
            "median_time": statistics.median(valid_times) if valid_times else 0,
            "std_dev": statistics.stdev(valid_times) if len(valid_times) > 1 else 0,
            "target_met": statistics.mean(valid_times) <= 3.0 if valid_times else False,
            "success_rate": len(valid_times) / len(times) * 100,
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate percentiles
        if valid_times:
            stats["p50"] = np.percentile(valid_times, 50)
            stats["p90"] = np.percentile(valid_times, 90)
            stats["p95"] = np.percentile(valid_times, 95)
            stats["p99"] = np.percentile(valid_times, 99)
        
        return stats
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive performance test of all services"""
        logger.info("🧪 Starting comprehensive performance test")
        
        # Test gateway health first
        try:
            response = requests.get(f"{self.gateway_url}/health", timeout=10)
            if response.status_code != 200:
                logger.error(f"Gateway health check failed: {response.status_code}")
                return {"error": "Gateway not available"}
        except Exception as e:
            logger.error(f"Gateway not accessible: {e}")
            return {"error": f"Gateway not accessible: {e}"}
        
        results = {
            "test_start": datetime.now().isoformat(),
            "gateway_url": self.gateway_url
        }
        
        # Test individual services
        results["resize"] = self.measure_resize_performance(10)
        results["detection"] = self.measure_detection_performance(3)  # Fewer iterations for AI
        results["filter"] = self.measure_filter_performance(10)
        results["pipeline"] = self.measure_pipeline_performance(3)  # Fewer for full pipeline
        
        results["test_end"] = datetime.now().isoformat()
        
        # Overall assessment
        self._assess_performance(results)
        
        return results
    
    def _assess_performance(self, results: Dict[str, Any]):
        """Assess overall performance against targets"""
        logger.info("\n📊 Performance Assessment Results:")
        logger.info("=" * 50)
        
        target_time = 3.0  # seconds
        
        for service in ["resize", "detection", "filter", "pipeline"]:
            if service in results and "avg_time" in results[service]:
                stats = results[service]
                avg_time = stats["avg_time"]
                success_rate = stats["success_rate"]
                target_met = avg_time <= target_time
                
                status = "✅ PASS" if target_met and success_rate >= 90 else "❌ FAIL"
                
                logger.info(f"{service.upper():>10}: {avg_time:.2f}s avg, {success_rate:.1f}% success - {status}")
                logger.info(f"{'':>10}  Range: {stats['min_time']:.2f}s - {stats['max_time']:.2f}s, P95: {stats.get('p95', 0):.2f}s")
        
        logger.info("=" * 50)
        logger.info("Target: ≤ 3.0 seconds average processing time")
        logger.info("Design Goal: 1-3 seconds (vs 60-94 seconds old system)")

def main():
    """Run performance monitoring"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="ImageFlowCanvas Performance Monitor")
    parser.add_argument("--gateway-url", default="http://localhost:8080", 
                       help="gRPC Gateway URL (default: http://localhost:8080)")
    parser.add_argument("--service", choices=["resize", "detection", "filter", "pipeline", "all"],
                       default="all", help="Service to test (default: all)")
    parser.add_argument("--iterations", type=int, default=5,
                       help="Number of test iterations (default: 5)")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(args.gateway_url)
    
    if args.service == "all":
        results = monitor.run_comprehensive_test()
    elif args.service == "resize":
        results = {"resize": monitor.measure_resize_performance(args.iterations)}
    elif args.service == "detection":
        results = {"detection": monitor.measure_detection_performance(args.iterations)}
    elif args.service == "filter":
        results = {"filter": monitor.measure_filter_performance(args.iterations)}
    elif args.service == "pipeline":
        results = {"pipeline": monitor.measure_pipeline_performance(args.iterations)}
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    # Exit with non-zero if any service failed to meet targets
    if args.service == "all":
        failed_services = []
        for service in ["resize", "detection", "filter", "pipeline"]:
            if service in results and "avg_time" in results[service]:
                if results[service]["avg_time"] > 3.0 or results[service]["success_rate"] < 90:
                    failed_services.append(service)
        
        if failed_services:
            logger.error(f"Performance targets not met for: {', '.join(failed_services)}")
            sys.exit(1)
        else:
            logger.info("🎉 All performance targets met!")
            sys.exit(0)

if __name__ == "__main__":
    main()