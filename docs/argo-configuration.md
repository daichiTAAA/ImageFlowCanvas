# Argo Workflows Configuration

This document describes the environment variables used to configure the Argo Workflows integration in ImageFlowCanvas.

## Required Environment Variables

### ARGO_SERVER_URL
- **Description**: URL of the Argo Workflows server
- **Default**: `http://argo-server.argo.svc.cluster.local:2746`
- **Example**: `http://argo-server.argo.svc.cluster.local:2746`

### ARGO_NAMESPACE
- **Description**: Kubernetes namespace where workflows are executed
- **Default**: `argo`
- **Example**: `argo`

### WORKFLOW_TEMPLATE
- **Description**: Name of the workflow template to use for pipeline execution
- **Default**: `dynamic-image-processing`
- **Example**: `dynamic-image-processing`

## Optional Environment Variables

### ARGO_TIMEOUT
- **Description**: Timeout for HTTP requests to Argo server (seconds)
- **Default**: `300`
- **Example**: `300`

### ARGO_MAX_RETRIES
- **Description**: Maximum number of retry attempts when workflow submission fails
- **Default**: `3`
- **Example**: `3`

### ARGO_RETRY_DELAY
- **Description**: Delay between retry attempts (seconds)
- **Default**: `30`
- **Example**: `30`

## Example Configuration

Create a `.env` file in the backend directory:

```bash
# Argo Workflows Configuration
ARGO_SERVER_URL=http://argo-server.argo.svc.cluster.local:2746
ARGO_NAMESPACE=argo
WORKFLOW_TEMPLATE=dynamic-image-processing
ARGO_TIMEOUT=300
ARGO_MAX_RETRIES=3
ARGO_RETRY_DELAY=30
```

## Health Check

You can check the Argo Workflows service health using the API endpoint:

```bash
curl http://localhost:8000/health/argo
```

This will return information about the Argo server accessibility and configuration.

## Troubleshooting

### Common Issues

1. **"Argo Workflowsへの委譲に失敗しました"**
   - Check if Argo server is accessible at the configured URL
   - Verify the namespace exists in your Kubernetes cluster
   - Ensure the workflow template is deployed

2. **Connection Timeout**
   - Increase `ARGO_TIMEOUT` value
   - Check network connectivity to Argo server

3. **Authentication Issues**
   - Ensure proper RBAC permissions are configured
   - Check if authentication is required for your Argo installation

### Debug Steps

1. Check Argo health: `GET /health/argo`
2. Review application logs for detailed error messages
3. Verify Argo server is running: `kubectl get pods -n argo`
4. Check workflow template exists: `kubectl get workflowtemplate -n argo`