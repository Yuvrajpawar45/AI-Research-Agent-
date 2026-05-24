"""
Web Search Tool — uses Tavily (free tier: 1000 searches/month)
Get your free key at: https://app.tavily.com
"""

import requests
import config


class WebSearchTool:
    BASE_URL = "https://api.tavily.com/search"

    def __init__(self):
        if not config.TAVILY_API_KEY:
            raise ValueError(
                "TAVILY_API_KEY not set.\n"
                "Get a free key at https://app.tavily.com and add it to .env"
            )
        self.api_key = config.TAVILY_API_KEY

    def search(self, query: str, max_results: int = None) -> list[dict]:
        """
        Search the web and return a list of source dicts:
        {title, url, content, score, published_date}
        """
        n = max_results or config.SOURCES_PER_QUERY
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": n,
            "search_depth": "advanced",   # better quality, still free
            "include_answer": False,
            "include_raw_content": False,
        }

        resp = requests.post(self.BASE_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        sources = []
        for r in data.get("results", []):
            sources.append({
                "title":          r.get("title", ""),
                "url":            r.get("url", ""),
                "content":        r.get("content", ""),
                "score":          r.get("score", 0.0),
                "published_date": r.get("published_date", ""),
            })
        return sources
