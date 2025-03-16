"""
Search Service for QuoteChat API

This service provides a unified interface for searching content across
different types (movie quotes, song lyrics, memes) using enhanced search
capabilities from external APIs and web scraping.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import logging

from .lyrics_service import LyricsService
from .movie_quotes_service import MovieQuotesService
from .memes_service import MemesService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentType(str, Enum):
    MOVIE_QUOTE = "Movie Quote"
    SONG_LYRIC = "Song Lyric"
    MEME = "Meme"

class SearchService:
    """Service for searching content across different types."""
    
    def __init__(self, genius_token: Optional[str] = None):
        """
        Initialize the search service.
        
        Args:
            genius_token: Optional Genius API token for authenticated requests
        """
        self.lyrics_service = LyricsService(genius_token=genius_token)
        self.movie_quotes_service = MovieQuotesService()
        self.memes_service = MemesService()
    
    def search_content(self, query: str, content_type: ContentType, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for content of the specified type.
        
        Args:
            query: Search query string
            content_type: Type of content to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing search results
        """
        if content_type == ContentType.MOVIE_QUOTE:
            return self.movie_quotes_service.search_movie_quotes(query, max_results)
        elif content_type == ContentType.SONG_LYRIC:
            return self.lyrics_service.search_lyrics(query, max_results)
        elif content_type == ContentType.MEME:
            return self.memes_service.search_memes(query, max_results)
        else:
            logger.warning(f"Unknown content type: {content_type}")
            return []
    
    def get_popular_content(self, content_type: ContentType, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Get popular content of the specified type.
        
        Args:
            content_type: Type of content to get
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing popular content
        """
        if content_type == ContentType.MOVIE_QUOTE:
            # Use fallback database for popular content
            return self.movie_quotes_service.search_movie_quotes_fallback("", max_results)
        elif content_type == ContentType.SONG_LYRIC:
            # Use a list of popular songs for lyrics
            popular_queries = ["sweet dreams", "bohemian rhapsody", "imagine", "thriller", "hotel california"]
            results = []
            for query in popular_queries[:max_results]:
                query_results = self.lyrics_service.search_lyrics_fallback(query, 1)
                if query_results:
                    results.extend(query_results)
            return results[:max_results]
        elif content_type == ContentType.MEME:
            # Use fallback database for popular memes
            return self.memes_service.search_memes_fallback("", max_results)
        else:
            logger.warning(f"Unknown content type: {content_type}")
            return []
