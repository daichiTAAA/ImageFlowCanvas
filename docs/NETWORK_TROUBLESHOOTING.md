# Network Connectivity Troubleshooting

This document provides guidance for resolving Android network connectivity issues, particularly the localhost:80 redirect problem.

## Quick Diagnosis

If you're experiencing connection failures:

1. **Check the diagnostic output** in the app's settings screen
2. **Look for localhost:80 in error messages** - this indicates proxy interference
3. **Use the troubleshooting guide** provided in the diagnostic results

## Common Solutions

### Proxy Redirect Issue (localhost:80)
- **Symptom**: Error message contains "localhost/127.0.0.1:80"
- **Solution**: Check Wi-Fi proxy settings, disable VPN, clear app cache
- **Technical**: The app now aggressively bypasses proxy settings

### DNS Resolution Issues
- **Symptom**: "UnknownHostException" or "DNS resolution failed"
- **Solution**: Use IP addresses instead of hostnames
- **For emulator**: Always use `10.0.2.2` to reach host machine
- **For real device**: Use actual PC IP address (find with `ipconfig`)

### Connection Refused
- **Symptom**: "Connection refused"
- **Solution**: Ensure backend is running with `--host 0.0.0.0 --port 8000`
- **Check**: Firewall settings on PC, verify IP address

## Development Setup

### Backend Setup
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### App Configuration
- **Real Device**: `http://192.168.X.X:8000/api/v1`
- **Emulator**: `http://10.0.2.2:8000/api/v1`

## Enhanced Diagnostics

The app now provides:
- ✅ Detailed error categorization
- ✅ Specific troubleshooting guidance
- ✅ Network environment analysis
- ✅ Multiple connection strategies
- ✅ Platform-specific optimizations