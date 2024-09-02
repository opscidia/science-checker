import pandas as pd, redis, json
from typing import Any, Union
from haystack.pipelines import Pipeline
from haystack.document_stores.memory import InMemoryDocumentStore
from haystack.nodes import (
    SentenceTransformersRanker, FARMReader,
    JoinDocuments,
)
from haystack.schema import Document
from scispacy.abbreviation import AbbreviationDetector
from spacy import load as spacy_load, Language
from spacyfishing import EntityFishing
from .components import (
    DyBM25Retriever,
    DyMultihopEmbeddingRetriever
)




def token_pipeline() -> Language:
    """
    Return SciBERT SpaCy model with entityfishing
    """
    model = spacy_load("en_core_sci_scibert")
    model.add_pipe("abbreviation_detector")
    model.add_pipe(
        "entityfishing",
        config = {
            "extra_info": True,
            "api_ef_base": "http://entityfish:8090"
        }
    )
    return model

class EQA:
    # Models below are example of models that are open-source and can be used
    def __init__(
        self,
        dense: str = "sentence-transformers/multi-qa-mpnet-base-dot-v1",
        ranker: str = "sebastian-hofstaetter/distilbert-dot-tas_b-b256-msmarco",
        eqa: str = "deepset/roberta-base-squad2"
    ):
    
        self.dense_retriever = DyMultihopEmbeddingRetriever(
            embedding_model = dense,
            use_gpu = False,
            model_format = 'sentence_transformers',
            num_iterations = 2,
            top_k = 5
        )

        self.pipeline = Pipeline()
        self.pipeline.add_node(
            component = self.dense_retriever,
            name = "DenseRetriever",
            inputs = ["Query"]
        )
        self.pipeline.add_node(
            component = DyBM25Retriever(top_k = 5),
            name = "SparseRetriever",
            inputs = ["Query"]
        )
        self.pipeline.add_node(
            component = JoinDocuments(join_mode = 'reciprocal_rank_fusion'),
            name = "JoinDocuments",
            inputs = ["SparseRetriever", "DenseRetriever"]
        )
        self.pipeline.add_node(
            component = SentenceTransformersRanker(
                model_name_or_path = ranker,
                use_gpu = False,
                top_k = 5
            ),
            name = "Ranker",
            inputs = ["JoinDocuments"]
        )
        self.pipeline.add_node(
            component = FARMReader(
                model_name_or_path = eqa,
                use_gpu = False,
                max_seq_len = 512,
            ),
            name = "Reader",
            inputs = ["Ranker"]
        )
        self.pipeline.metrics_filter = {"DenseRetriever": ["recall_single_hit"]}
        self.cache = redis.Redis(
            host = 'redis',
            port = 6379,
            decode_responses = True
        )
    

    def _set_cache(self, data: dict[str, list[float]]) -> None:
        """
        Private. Set cache
        :param data: article ids as keys and embeddings as values
        """
        data = {k: json.dumps(v) for k, v in data.items()}
        self.cache.mset(data)
    

    def _get_cache(self, keys: list[str]) -> dict[str, list[float]]:
        """
        Private. Get cache
        :param keys: list of article ids
        :return: dictionary of article ids and embeddings
        """
        cached = dict(
            zip(
                keys,
                [
                    json.loads(value)
                    if value else None
                    for value in self.cache.mget(keys)
                ]
            )
        )
        return cached

    

    def _predict(
        self,
        query: str,
        document_store: InMemoryDocumentStore
    ):
        """
        Private. Run pipeline
        """
        return self.pipeline.run(
            query = query,
            params = dict(
                SparseRetriever = dict(document_store = document_store),
                DenseRetriever = dict(document_store = document_store),
            )
        )
    
    
    @staticmethod
    def _qa_format(
        articles: list[dict[str, str]],
        predictions: dict[str, Any]
    ) -> list[dict[str, Union[str, list[str], float]]]:
        """
        Private. Format articles to include predictions
        :param articles: list of articles
        :param predictions: predictions dictionary
        :return: list of formatted articles
        """

        def highlight_answer(row: pd.Series) -> str:
            """
            Highlight the answer and score in its context in the content text
            :param row: row of the dataframe
            :return: content text with highlighted answer and context
            """
            content = row['content']
            contexts = row['context']
            answers = row['answer']
            scores = row['anscore']
            
            if not isinstance(contexts, list):
                return content

            for context, answer, score in zip(contexts, answers, scores):
                score = f'{score:.2f}%'
                content = content.replace(context, f'<span class="hglt__context">{context}</span>')
                content = content.replace(answer, f'<span class="hglt__answer" score="{score}">{answer}</span>')
            return content

        
        answers = (
            pd.DataFrame(
                predictions['answers'],
                columns=['document_ids', 'score', 'context', 'answer']
            )
            .explode('document_ids')
            .rename(columns={'document_ids': 'id'})
            .assign(anscore = lambda x: x['score'] * 100)
            .drop(columns=['score'])
            .groupby('id')
            .agg(list)
            .reset_index()
        )

        results = (
            pd.DataFrame(articles)
            .merge(
                pd.DataFrame(predictions['documents'], columns=['id', 'score']),
                on = 'id',
                how = 'left'
            )
            .assign(score = lambda x: x['score'].fillna(0) * 100)
            .merge(
                answers,
                on = 'id',
                how = 'left'
            )
            .fillna('[]')
            .assign(content = lambda x: x.apply(highlight_answer, axis=1))
            .sort_values('score', ascending=False)
        )

        return results.to_dict(orient='records')
    

    def __call__(
        self,
        query: str,
        document_store: InMemoryDocumentStore,
        articles: list[dict[str, Any]]
    ):
        """
        Call method to be used in WS server
        """
        predictions = self._predict(query, document_store)
        return self._qa_format(articles, predictions)


    def create_document_store(
        self,
        documents: list[dict[str, str]]
    ) -> InMemoryDocumentStore:
        """
        Create document store
        :param documents: List of documents with id and abstracts
        :return: InMemoryDocumentStore with embedded documents
        """
        document_store = InMemoryDocumentStore(
            use_bm25 = True,
            use_gpu = False
        )
        cached_embeddings = self._get_cache([doc['id'] for doc in documents])
        document_store.write_documents([
            Document(
                id = doc['id'],
                content = doc['content'],
                embedding = cached_embeddings.get(doc['id'], None)
            ) for doc in documents
        ])
        document_store.update_embeddings(self.dense_retriever)
        self._set_cache({
            doc.id: doc.embedding for doc in document_store.get_all_documents()
        })
        return document_store
        

