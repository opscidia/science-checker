import os, uvicorn

HOST = os.getenv('API_HOST', '0.0.0.0')
PORT = int(os.getenv('API_PORT', '5000'))
WORKERS = int(os.getenv('API_WORKERS', '1'))

if __name__ == "__main__":
    uvicorn.run(
        "api_science_checker:app",
        host = HOST, port = PORT,
        reload = False, workers = WORKERS,
        log_config = "../conf/api.ini"
    )