gRPC Desktop Streaming (JVM)

Overview
- Backend now exposes `CameraStreamProcessor.ProcessVideoStream` on `0.0.0.0:50051` (configurable via `DESKTOP_GRPC_BIND_ADDR`).
- Protocol: `proto/imageflow/v1/camera_stream.proto` (reuses existing messages and `Detection` from `ai_detection.proto`).
- Auth: Send `authorization: Bearer <JWT>` metadata on every call.
- Transport: Async gRPC bridge (grpc.aio) pass-through to upstream camera-stream service.
- Security: Optional TLS on the desktop gRPC endpoint via `DESKTOP_GRPC_TLS_CERT` and `DESKTOP_GRPC_TLS_KEY`.

Gradle (desktop JVM)
- Add dependencies:
  - `io.grpc:grpc-netty-shaded:1.62.2`
  - `io.grpc:grpc-protobuf:1.62.2`
  - `io.grpc:grpc-stub:1.62.2`
  - `com.google.protobuf:protobuf-java:3.25.3`
- Add the protobuf Gradle plugin to generate Java/Kotlin stubs from `proto/` in this repo. Example:

plugins {
  id("com.google.protobuf") version "0.9.4"
}

protobuf {
  protoc { artifact = "com.google.protobuf:protoc:3.25.3" }
  plugins {
    id("grpc") { artifact = "io.grpc:protoc-gen-grpc-java:1.62.2" }
  }
  generateProtoTasks {
    all().forEach { task ->
      task.plugins { id("grpc") }
      task.builtins { id("java") }
    }
  }
}

sourceSets {
  val main by getting {
    proto.srcDir("${project.rootDir}/proto")
  }
}

Client usage (Kotlin/JVM)

import io.grpc.ManagedChannelBuilder
import io.grpc.Metadata
import io.grpc.stub.MetadataUtils
import imageflow.v1.CameraStreamProcessorGrpc
import imageflow.v1.CameraStream

val channel = ManagedChannelBuilder
  .forTarget("localhost:50051") // or backend host
  .usePlaintext() // For TLS, configure .useTransportSecurity() and trust store
  .build()

// Attach JWT to metadata
val jwt = /* read stored token */
val authMd = Metadata().apply {
  val key = Metadata.Key.of("authorization", Metadata.ASCII_STRING_MARSHALLER)
  put(key, "Bearer $jwt")
}

val baseStub = CameraStreamProcessorGrpc.newStub(channel)
val stub = MetadataUtils.attachHeaders(baseStub, authMd)

val responseObserver = object : io.grpc.stub.StreamObserver<CameraStream.ProcessedFrame> {
  override fun onNext(value: CameraStream.ProcessedFrame) {
    // Update UI: value.detectionsList, value.processingTimeMs, value.errorMessage, etc.
  }

  override fun onError(t: Throwable) {
    // Show error
  }

  override fun onCompleted() {
    // Stream finished
  }
}

val requestObserver = stub.processVideoStream(responseObserver)

// Send each frame (JPEG/PNG bytes) as it’s captured
fun sendFrame(bytes: ByteArray, width: Int, height: Int, sourceId: String, pipelineId: String = "ai_detection") {
  val meta = CameraStream.VideoMetadata.newBuilder()
    .setSourceId(sourceId)
    .setWidth(width)
    .setHeight(height)
    .setPipelineId(pipelineId)
    .build()

  val frame = CameraStream.VideoFrame.newBuilder()
    .setFrameData(com.google.protobuf.ByteString.copyFrom(bytes))
    .setTimestampMs(System.currentTimeMillis())
    .setMetadata(meta)
    .build()

  requestObserver.onNext(frame)
}

// When done streaming
// requestObserver.onCompleted()

Notes
- The backend verifies JWT in gRPC metadata. Reuse your existing login flow to obtain the token.
- The backend bridges frames asynchronously to the internal camera-stream service and returns detections and timing.
- If you need to pass dynamic parameters (e.g., model name), populate `VideoMetadata.processing_params` map.
- In production, prefer TLS: set `DESKTOP_GRPC_TLS_CERT` and `DESKTOP_GRPC_TLS_KEY` on the backend and use `useTransportSecurity()` on the client with proper trust.
