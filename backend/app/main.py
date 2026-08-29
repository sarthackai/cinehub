from fastapi import FastAPI

app = FastAPI(title="StreamSync AI Backend")


@app.get("/")
def read_root():
    return {"status": "ok", "message": "StreamSync AI backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}