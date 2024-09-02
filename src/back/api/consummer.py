from fastapi import WebSocket
from typing import Callable




class Discussion:
    def __init__(self, client_id: str, websocket: WebSocket):
        self.client_id = client_id
        self.websocket = websocket
        self.document_store = None
        self.articles = list()
    
    async def select_articles(
        self,
        method: Callable,
        articles: list[dict[str, str]],
    ):
        """
        Create document store
        """
        self.articles = articles
        self.document_store = method(articles)
    
    async def discuss(
        self,
        method: Callable,
        query: str,
    ):
        """
        Discuss with selection of articles
        """
        return method(query, self.document_store, self.articles)
    