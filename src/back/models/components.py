from haystack.nodes import (
    MultihopEmbeddingRetriever,
    BM25Retriever
)
from haystack.schema import Document
from spacy.lang.en import English
from scispacy.abbreviation import AbbreviationDetector
from spacyfishing import EntityFishing
from typing import Optional, Any




class DynamicRetriever:
    def run(
        self,
        root_node: str,
        query: Optional[str] = None,
        filters: Optional[Any] = None,
        top_k: Optional[int] = None,
        documents: Optional[list[Document]] = None,
        index: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        scale_score: Optional[bool] = None,
        document_store = None,
    ):
        old_document_store = self.document_store
        if document_store is not None:
            self.document_store = document_store
        result = super().run(
            root_node, query,
            filters, top_k,
            documents, index,
            headers, scale_score,
        )
        if old_document_store is not None:
            self.document_store = old_document_store
        return result




class DyBM25Retriever(DynamicRetriever, BM25Retriever):
    pass




class DyMultihopEmbeddingRetriever(DynamicRetriever, MultihopEmbeddingRetriever):
    pass



