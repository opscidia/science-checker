import os, uvicorn

HOST = os.getenv('API_HOST', '0.0.0.0')
PORT = int(os.getenv('API_PORT', '8000'))
WORKERS = int(os.getenv('API_WORKERS', '-1'))

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host = HOST, port = PORT,
        reload = False, workers = WORKERS,
    )