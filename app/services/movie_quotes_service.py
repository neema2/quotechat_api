"""
Movie Quotes Service for QuoteChat API

This service provides enhanced movie quotes search functionality by integrating with:
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

class MovieQuotesService:
    """Service for fetching and searching movie quotes from multiple sources."""
    
    def __init__(self):
        """Initialize the movie quotes service."""
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
        
        # Fallback movie quotes database
        self.movie_quotes = [
            {"content": "I'll be back.", "source": "Terminator"},
            {"content": "May the Force be with you.", "source": "Star Wars"},
            {"content": "You talking to me?", "source": "Taxi Driver"},
            {"content": "Here's looking at you, kid.", "source": "Casablanca"},
            {"content": "I feel the need... the need for speed!", "source": "Top Gun"},
            {"content": "Houston, we have a problem.", "source": "Apollo 13"},
            {"content": "Life is like a box of chocolates.", "source": "Forrest Gump"},
            {"content": "There's no place like home.", "source": "The Wizard of Oz"},
            {"content": "I'm the king of the world!", "source": "Titanic"},
            {"content": "You can't handle the truth!", "source": "A Few Good Men"},
        ]
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent to avoid detection as a bot."""
        return random.choice(self.user_agents)
    
    def search_movie_quotes_google(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for movie quotes using Google search.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing movie quote information
        """
        search_query = f"{query} famous movie quote"
        url = f"https://www.google.com/search?q={search_query}"
        
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
            
            # Look for quote boxes or featured snippets
            quote_box = soup.find('div', class_='kp-blk')
            if quote_box:
                quote_text = quote_box.find('div', class_='BNeawe')
                if quote_text:
                    # Try to extract movie title
                    movie_title = "Unknown Movie"
                    title_element = quote_box.find('span', class_='BNeawe')
                    if title_element:
                        movie_title = title_element.text
                    
                    results.append({
                        "content": quote_text.text.strip(),
                        "source": movie_title,
                        "relevanceScore": 1.0
                    })
            
            # Look for other quote sources in search results
            search_results = soup.find_all('div', class_='g')
            for result in search_results:
                title_element = result.find('h3')
                if not title_element:
                    continue
                
                title = title_element.text
                if 'quote' in title.lower() or 'movie' in title.lower():
                    link_element = result.find('a')
                    if link_element and 'href' in link_element.attrs:
                        link = link_element['href']
                        
                        # Extract snippet if available
                        snippet_element = result.find('div', class_='VwiC3b')
                        snippet = snippet_element.text if snippet_element else ""
                        
                        # Only add if we have some content and it looks like a quote
                        if snippet and ('"' in snippet or '"' in snippet):
                            # Try to extract the quote from the snippet
                            quote_match = re.search(r'[""]([^""]+)[""]', snippet)
                            if quote_match:
                                quote = quote_match.group(1)
                                results.append({
                                    "content": quote,
                                    "source": title,
                                    "relevanceScore": 0.8
                                })
            
            # Return limited number of results
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching Google for movie quotes: {str(e)}")
            return []
    
    def search_movie_quotes_fallback(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for movie quotes using the fallback database with fuzzy matching.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing movie quote information
        """
        results = []
        query = query.lower()
        
        for i, item in enumerate(self.movie_quotes):
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
    
    def search_movie_quotes(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for movie quotes using multiple sources.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing movie quote information
        """
        # Search using Google
        google_results = self.search_movie_quotes_google(query, max_results=max_results//2)
        
        # Search using fallback database
        fallback_results = self.search_movie_quotes_fallback(query, max_results=max_results//2)
        
        # Combine results
        all_results = google_results + fallback_results
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x.get('relevanceScore', 0), reverse=True)
        
        # Return limited number of results
        return all_results[:max_results]
