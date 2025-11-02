import pytest
from crawling import search_urls  # Предполагаем, что функция будет в crawling.py

def test_search_urls():
    query = "Ольга Розет дизайнер"
    results = search_urls(query, num_results=5)
    assert len(results) > 0
    assert all(isinstance(url, str) for url in results)

