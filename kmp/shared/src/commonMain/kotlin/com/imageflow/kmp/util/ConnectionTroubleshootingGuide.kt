package com.imageflow.kmp.util

/**
 * Connection troubleshooting guide for users experiencing localhost:80 redirect issues
 */
object ConnectionTroubleshootingGuide {
    
    fun getGuidanceForError(errorMessage: String?): String {
        return when {
            errorMessage?.contains("localhost") == true || errorMessage?.contains("127.0.0.1:80") == true -> {
                """
                🚨 PROXY REDIRECT DETECTED
                
                Your connection is being redirected to localhost:80, which indicates a proxy configuration issue.
                
                SOLUTIONS TO TRY:
                1. Check Wi-Fi proxy settings on your device
                2. Disable any VPN connections
                3. Check for corporate/MDM proxy policies
                4. Try using airplane mode then reconnect to Wi-Fi
                5. For emulator: Use 10.0.2.2 instead of localhost
                6. For real device: Use the actual PC IP address (e.g., 192.168.0.9)
                
                TECHNICAL DETAILS:
                - The app explicitly disables proxy usage
                - This redirect happens at the OS/network level
                - Browser works because it may use different proxy settings
                """.trimIndent()
            }
            
            errorMessage?.contains("Connection refused") == true -> {
                """
                🔌 CONNECTION REFUSED
                
                The server is not accepting connections on the specified port.
                
                SOLUTIONS TO TRY:
                1. Ensure the backend server is running: uvicorn app.main:app --host 0.0.0.0 --port 8000
                2. Check firewall settings on the PC (allow port 8000)
                3. Verify the IP address is correct
                4. Test the URL in a browser first
                """.trimIndent()
            }
            
            errorMessage?.contains("timeout") == true -> {
                """
                ⏱️ CONNECTION TIMEOUT
                
                The connection is taking too long to establish.
                
                SOLUTIONS TO TRY:
                1. Check network connectivity (both devices on same network)
                2. Move closer to Wi-Fi router
                3. Restart Wi-Fi connection on device
                4. Check for network congestion
                """.trimIndent()
            }
            
            errorMessage?.contains("UnknownHostException") == true -> {
                """
                🌐 DNS RESOLUTION FAILED
                
                The device cannot resolve the hostname/IP address.
                
                SOLUTIONS TO TRY:
                1. Use IP address instead of hostname
                2. Check network DNS settings
                3. For emulator: Use 10.0.2.2 for host machine
                4. Verify IP address with: ipconfig (Windows) or ifconfig (Mac/Linux)
                """.trimIndent()
            }
            
            else -> {
                """
                🔍 GENERAL CONNECTION TROUBLESHOOTING
                
                BASIC CHECKS:
                1. Ensure both devices are on the same Wi-Fi network
                2. Test the URL in device browser first
                3. Check server is running: backend should show "Server started on 0.0.0.0:8000"
                4. Verify URL format: http://IP:8000/v1 (no extra paths)
                
                NETWORK SETUP:
                - Real device: Use PC's IP address (e.g., http://192.168.0.9:8000/v1)
                - Emulator: Use http://10.0.2.2:8000/v1
                - Always use HTTP (not HTTPS) for local development
                """.trimIndent()
            }
        }
    }
    
    fun getQuickFixCommands(): List<String> {
        return listOf(
            "Check PC IP: ipconfig getifaddr en0 (Mac) or ipconfig (Windows)",
            "Start backend: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000",
            "Test in browser: http://YOUR_PC_IP:8000/v1/products",
            "Emulator URL: http://10.0.2.2:8000/v1",
            "Real device URL: http://YOUR_PC_IP:8000/v1"
        )
    }
    
    fun getEnvironmentSpecificGuidance(isEmulator: Boolean, detectedIssues: List<String>): String {
        val guidance = mutableListOf<String>()
        
        if (isEmulator) {
            guidance.add("📱 ANDROID EMULATOR SETUP:")
            guidance.add("- Use 10.0.2.2 to reach host machine")
            guidance.add("- URL format: http://10.0.2.2:8000/v1")
            guidance.add("- Backend must run with --host 0.0.0.0")
        } else {
            guidance.add("📱 REAL DEVICE SETUP:")
            guidance.add("- Use PC's actual IP address")
            guidance.add("- Find IP: Settings > Network or ipconfig command")
            guidance.add("- URL format: http://192.168.X.X:8000/v1")
            guidance.add("- Ensure same Wi-Fi network")
        }
        
        if (detectedIssues.isNotEmpty()) {
            guidance.add("")
            guidance.add("⚠️ DETECTED ISSUES:")
            detectedIssues.forEach { issue ->
                guidance.add("- $issue")
            }
        }
        
        return guidance.joinToString("\n")
    }
}
