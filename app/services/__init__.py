"""
Services package for QuoteChat API.

This package contains services for searching and retrieving content
from various sources, including:
- Lyrics from Genius.com and Google search
- Movie quotes from Google search and fallback database
- Memes from Google search and fallback database
"""

from .lyrics_service import LyricsService
from .movie_quotes_service import MovieQuotesService
from .memes_service import MemesService

__all__ = ['LyricsService', 'MovieQuotesService', 'MemesService']
