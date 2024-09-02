from contextlib import asynccontextmanager
from fastapi import (
    FastAPI, WebSocket,
    WebSocketException
)
from fastapi.middleware.cors import CORSMiddleware
from models.utils import (
    token_pipeline,
    EQA
)
from nltk.corpus import wordnet as wn
from .consummer import Discussion
from .search import search_articles, get_article_by_id

wn.ensure_loaded()
import warnings
warnings.filterwarnings('ignore')


pipes = dict()
@asynccontextmanager
async def pipelines(*args, **kwargs):
    """
    Load pipelines
    """
    pipes['token'] = token_pipeline()
    pipes['EQA'] = EQA()
    yield
    pipes.clear()




app = FastAPI(
    title = "Science Checker API",
    description = "API for Science Checker",
    version = "0.0.1",
    lifespan = pipelines
)




origins = [
    "http://localhost:3000",  # Your frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.get("/")
async def root():
    return {"message": "Hello World"}




@app.get(
    "/api/search",
    summary = "Search articles to answer questions",
)
def search(query: str):
    response = search_articles(query, pipes['token'])
    return response




@app.get(
    "/api/article/{id}",
    summary = "Get article",
)
def get_article(id: str):
    article = get_article_by_id(id)
    return article




@app.websocket(
    "/ws/{client_id}",
)
async def discuss(
    websocket: WebSocket,
    client_id: str,
):
    """Discuss with selection of articles"""
    await websocket.accept()
    discussion = Discussion(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'select_articles':
                await discussion.select_articles(pipes['EQA'].create_document_store, data['articles'])
                await websocket.send_json({"message": "Articles selected"})
            elif data['type'] == 'discuss':
                results = await discussion.discuss(pipes['EQA'], data['query'])
                await websocket.send_json(dict(
                    type = 'question.answered',
                    data = results
                ))
            else:
                await websocket.send_json({"error": "Invalid type"})
    except WebSocketException:
        pass