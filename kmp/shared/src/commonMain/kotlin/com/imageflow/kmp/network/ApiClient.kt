package com.imageflow.kmp.network

interface ApiClient {
    val grpc: GrpcClient
    val ws: WebSocketClient
    val rest: RestClient
}

