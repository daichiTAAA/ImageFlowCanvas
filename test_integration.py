#!/usr/bin/env python3
"""
Integration test for camera stream gRPC service
Tests that the service can start and accept basic gRPC calls
"""

import sys
import os
import time
import asyncio
import grpc
from concurrent import futures
import threading
import signal

# Add generated proto path
sys.path.append('generated/python')

from imageflow.v1 import camera_stream_pb2
from imageflow.v1 import camera_stream_pb2_grpc

# Import our server implementation
sys.path.append('services/camera-stream-grpc-app/src')
from camera_stream_grpc_server import CameraStreamProcessorImplementation, HealthServiceImplementation

class IntegrationTester:
    def __init__(self):
        self.server = None
        self.server_thread = None
        self.port = 9095  # Use a test-specific port
        
    def start_server(self):
        """Start the gRPC server in a separate thread"""
        def run_server():
            self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
            
            # Add services
            camera_stream_pb2_grpc.add_CameraStreamProcessorServicer_to_server(
                CameraStreamProcessorImplementation(), self.server
            )
            
            # Add health service
            from grpc_health.v1 import health_pb2_grpc
            health_pb2_grpc.add_HealthServicer_to_server(
                HealthServiceImplementation(), self.server
            )
            
            self.server.add_insecure_port(f'[::]:{self.port}')
            self.server.start()
            print(f"✓ Test gRPC server started on port {self.port}")
            
            try:
                self.server.wait_for_termination()
            except KeyboardInterrupt:
                pass
        
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
    
    def stop_server(self):
        """Stop the gRPC server"""
        if self.server:
            self.server.stop(0)
            print("✓ Test gRPC server stopped")
    
    def test_streaming(self):
        """Test bidirectional streaming"""
        print("Testing bidirectional streaming...")
        
        try:
            # Create gRPC channel
            channel = grpc.insecure_channel(f'localhost:{self.port}')
            stub = camera_stream_pb2_grpc.CameraStreamProcessorStub(channel)
            
            # Create test frames
            test_frames = []
            for i in range(3):
                frame = camera_stream_pb2.VideoFrame()
                frame.frame_data = f"test_frame_{i}".encode()
                frame.timestamp_ms = int(time.time() * 1000) + i * 100
                
                metadata = frame.metadata
                metadata.source_id = "test_camera"
                metadata.width = 640
                metadata.height = 480
                metadata.pipeline_id = "passthrough"
                
                test_frames.append(frame)
            
            # Test streaming (synchronous)
            def frame_generator():
                for frame in test_frames:
                    print(f"  Sending frame for {frame.metadata.source_id}")
                    yield frame
            
            # Start streaming
            response_stream = stub.ProcessVideoStream(frame_generator())
            
            # Collect responses
            responses = []
            for response in response_stream:
                print(f"  Received response: source={response.source_id}, status={response.status}")
                responses.append(response)
            
            # Validate responses
            assert len(responses) == len(test_frames), f"Expected {len(test_frames)} responses, got {len(responses)}"
            
            for i, response in enumerate(responses):
                assert response.source_id == "test_camera", f"Wrong source_id in response {i}"
                assert response.status == camera_stream_pb2.STREAM_PROCESSING_STATUS_SUCCESS, f"Wrong status in response {i}"
            
            print("✓ Bidirectional streaming test passed")
            
        except Exception as e:
            print(f"✗ Streaming test failed: {e}")
            raise
        finally:
            channel.close()
    
    def test_health_check(self):
        """Test health check endpoint"""
        print("Testing health check...")
        
        try:
            from grpc_health.v1 import health_pb2, health_pb2_grpc
            
            channel = grpc.insecure_channel(f'localhost:{self.port}')
            health_stub = health_pb2_grpc.HealthStub(channel)
            
            # Make health check request
            request = health_pb2.HealthCheckRequest()
            response = health_stub.Check(request)
            
            assert response.status == health_pb2.HealthCheckResponse.SERVING, "Service not serving"
            
            print("✓ Health check test passed")
            
        except Exception as e:
            print(f"✗ Health check test failed: {e}")
            raise
        finally:
            channel.close()

def main():
    print("Starting Camera Stream gRPC Integration Test")
    print("=" * 50)
    
    tester = IntegrationTester()
    
    try:
        # Start server
        tester.start_server()
        
        # Run tests
        tester.test_health_check()
        tester.test_streaming()
        
        print("\n" + "=" * 50)
        print("✓ ALL INTEGRATION TESTS PASSED")
        print("✓ Camera stream gRPC service is working correctly")
        
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        return 1
    finally:
        tester.stop_server()
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)