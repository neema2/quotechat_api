"""
Memes Service for QuoteChat API

This service provides enhanced memes search functionality by integrating with:
1. Google search (via web scraping with requests and BeautifulSoup)
2. In-memory database with fuzzy search as fallback
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import List, Dict, Any, Optional
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemesService:
    """Service for fetching and searching memes from multiple sources."""
    
    def __init__(self):
        """Initialize the memes service."""
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
        
        # Fallback memes database
        self.memes = [
            {"content": "One does not simply walk into Mordor.", "source": "Boromir Meme"},
            {"content": "This is fine.", "source": "KC Green Comic"},
            {"content": "Shut up and take my money!", "source": "Futurama Meme"},
            {"content": "I don't always test my code, but when I do, I do it in production.", "source": "The Most Interesting Man in the World"},
            {"content": "It's over 9000!", "source": "Dragon Ball Z"},
            {"content": "Why not Zoidberg?", "source": "Futurama Meme"},
            {"content": "Ain't nobody got time for that!", "source": "Sweet Brown Interview"},
            {"content": "Such wow. Very amaze.", "source": "Doge Meme"},
            {"content": "But that's none of my business.", "source": "Kermit the Frog Meme"},
            {"content": "Hide the pain Harold.", "source": "Stock Photo Meme"},
        ]
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent to avoid detection as a bot."""
        return random.choice(self.user_agents)
    
    def search_memes_google(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for memes using Google search.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing meme information
        """
        search_query = f"{query} meme"
        url = f"https://www.google.com/search?q={search_query}&tbm=isch"
        
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Extract meme text from search results
            search_results = soup.find_all('div', class_='g')
            for result in search_results:
                title_element = result.find('h3')
                if not title_element:
                    continue
                
                title = title_element.text
                if 'meme' in title.lower():
                    # Extract snippet if available
                    snippet_element = result.find('div', class_='VwiC3b')
                    snippet = snippet_element.text if snippet_element else ""
                    
                    # Only add if we have some content
                    if snippet:
                        results.append({
                            "content": snippet,
                            "source": title,
                            "relevanceScore": 0.8
                        })
            
            # Return limited number of results
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching Google for memes: {str(e)}")
            return []
    
    def search_memes_fallback(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for memes using the fallback database with fuzzy matching.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing meme information
        """
        results = []
        query = query.lower()
        
        for i, item in enumerate(self.memes):
            content = item["content"].lower()
            source = item["source"]
            
            # Calculate relevance score
            score = 0
            
            # Exact match
            if query == content:
                score = 1.0
            # Contains match
            elif query in content:
                score = 0.8
            # Word-level matching
            else:
                query_words = query.split()
                content_words = content.split()
                
                for q_word in query_words:
                    for c_word in content_words:
                        if q_word == c_word:
                            score += 0.2
                        elif q_word in c_word:
                            score += 0.1
            
            if score > 0:
                results.append({
                    "content": item["content"],
                    "source": source,
                    "relevanceScore": score
                })
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get('relevanceScore', 0), reverse=True)
        
        # Return limited number of results
        return results[:max_results]
    
    def search_memes(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for memes using multiple sources.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing meme information
        """
        # Search using both methods
        google_results = self.search_memes_google(query, max_results=max_results//2)
        fallback_results = self.search_memes_fallback(query, max_results=max_results//2)
        
        # Combine results
        all_results = google_results + fallback_results
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x.get('relevanceScore', 0), reverse=True)
        
        # Return limited number of results
        return all_results[:max_results]
