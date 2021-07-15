from utils.es_utils import get_terms_articles
from collections import Counter

def get_corpus(**kwargs):
    """
    Get corpus yearly
    first: str.
    second: str.
    index: str.
    :return: {year: int, }. Dict of count by year
    """
    first, second = kwargs['first'], [kwargs['second']]
    index = kwargs['index']
    articles = get_terms_articles(first, second, index)
    return dict(sorted(Counter(
        map(lambda x: x['publication_date'][:4],
                    articles)).items()))