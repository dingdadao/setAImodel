source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > log.txt 2>&1 &