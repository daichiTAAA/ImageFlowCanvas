# Backend API

# ローカル実行方法
```bash
# Copy generated protobuf files to service directory if needed
mkdir -p "./backend/generated"
cp -r "./generated/python" "./backend/generated/"
conda activate imageflowcanvas
cd backend
pip install -r requirements.txt
```

```bash
conda activate imageflowcanvas && cd ~/ImageFlowCanvas/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```