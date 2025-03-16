"""
Lyrics Service for QuoteChat API

This service provides enhanced lyrics search functionality by integrating with:
1. Genius.com API (via lyricsgenius library)
2. Google search (via web scraping with requests and BeautifulSoup)
3. Chosic.com for additional lyric search capabilities
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import logging
from typing import List, Dict, Any, Optional
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LyricsService:
    """Service for fetching and searching song lyrics from multiple sources."""
    
    def __init__(self, genius_token: Optional[str] = None):
        """
        Initialize the lyrics service.
        
        Args:
            genius_token: Optional Genius API token for authenticated requests
        """
        self.genius_token = genius_token
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent to avoid detection as a bot."""
        return random.choice(self.user_agents)
    
    def search_lyrics_google(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for song lyrics using Google search.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing song information
        """
        search_query = f"{query} lyrics"
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
            
            # Look for lyrics in Google's OneBox result
            lyrics_box = soup.find('div', class_='hwc')
            if lyrics_box:
                # Extract song title and artist
                title_element = soup.find('div', class_='SPZz6b')
                artist_element = soup.find('div', class_='LGOjhe')
                
                title = title_element.text if title_element else "Unknown Title"
                artist = artist_element.text if artist_element else "Unknown Artist"
                
                # Extract lyrics text
                lyrics_text = ""
                lyrics_spans = lyrics_box.find_all('span')
                for span in lyrics_spans:
                    lyrics_text += span.text + "\n"
                
                if lyrics_text:
                    results.append({
                        "content": lyrics_text.strip(),
                        "source": f"{artist} - {title}",
                        "relevanceScore": 1.0
                    })
            
            # Look for other lyrics sources in search results
            search_results = soup.find_all('div', class_='g')
            for result in search_results:
                title_element = result.find('h3')
                if not title_element:
                    continue
                
                title = title_element.text
                if 'lyrics' in title.lower():
                    link_element = result.find('a')
                    if link_element and 'href' in link_element.attrs:
                        link = link_element['href']
                        
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
            logger.error(f"Error searching Google for lyrics: {str(e)}")
            return []
    
    def search_lyrics_genius(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for song lyrics using Genius.com API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing song information
        """
        # If no Genius token is provided, use web scraping instead of API
        if not self.genius_token:
            return self._search_lyrics_genius_scrape(query, max_results)
        
        # Use lyricsgenius library if token is available
        try:
            import lyricsgenius
            genius = lyricsgenius.Genius(self.genius_token)
            
            # Search for songs
            search_results = genius.search_songs(query)
            
            results = []
            if 'hits' in search_results:
                for hit in search_results['hits'][:max_results]:
                    song_info = hit.get('result', {})
                    
                    # Get song details
                    song_id = song_info.get('id')
                    title = song_info.get('title', 'Unknown Title')
                    artist = song_info.get('primary_artist', {}).get('name', 'Unknown Artist')
                    
                    # Get full lyrics if available
                    lyrics = ""
                    if song_id:
                        try:
                            song = genius.song(song_id)
                            lyrics = song.get('lyrics', '')
                        except Exception as e:
                            logger.warning(f"Error fetching lyrics for song {song_id}: {str(e)}")
                    
                    # Add to results
                    if lyrics:
                        results.append({
                            "content": lyrics,
                            "source": f"{artist} - {title}",
                            "relevanceScore": 0.9
                        })
            
            return results
            
        except ImportError:
            logger.warning("lyricsgenius library not available, falling back to web scraping")
            return self._search_lyrics_genius_scrape(query, max_results)
        except Exception as e:
            logger.error(f"Error searching Genius API for lyrics: {str(e)}")
            return []
    
    def _search_lyrics_genius_scrape(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for song lyrics by scraping Genius.com.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing song information
        """
        search_url = f"https://genius.com/api/search/song?q={query}"
        
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'response' in data and 'sections' in data['response']:
                for section in data['response']['sections']:
                    if section.get('type') == 'song':
                        hits = section.get('hits', [])
                        for hit in hits[:max_results]:
                            result = hit.get('result', {})
                            
                            title = result.get('title', 'Unknown Title')
                            artist = result.get('primary_artist', {}).get('name', 'Unknown Artist')
                            url = result.get('url')
                            
                            # Get lyrics from the song page if URL is available
                            lyrics = ""
                            if url:
                                try:
                                    lyrics = self._scrape_lyrics_from_genius_page(url)
                                except Exception as e:
                                    logger.warning(f"Error scraping lyrics from {url}: {str(e)}")
                            
                            # Add to results if we have lyrics
                            if lyrics:
                                results.append({
                                    "content": lyrics,
                                    "source": f"{artist} - {title}",
                                    "relevanceScore": 0.9
                                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Genius.com for lyrics: {str(e)}")
            return []
    
    def _scrape_lyrics_from_genius_page(self, url: str) -> str:
        """
        Scrape lyrics from a Genius.com song page.
        
        Args:
            url: URL of the Genius song page
            
        Returns:
            String containing the song lyrics
        """
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the lyrics container
        lyrics_container = soup.find('div', class_='lyrics')
        if not lyrics_container:
            # Try alternative container for newer Genius pages
            lyrics_container = soup.find('div', class_='Lyrics__Container-sc-1ynbvzw-6')
        
        if lyrics_container:
            # Extract and clean lyrics
            lyrics = lyrics_container.get_text()
            # Remove extra whitespace and normalize line breaks
            lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)
            return lyrics.strip()
        
        return ""
    
    def search_lyrics_chosic(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for song lyrics using Chosic.com.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing song information
        """
        search_url = "https://www.chosic.com/find-song-by-lyrics/"
        
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        try:
            # First get the search page to extract any necessary tokens
            session = requests.Session()
            response = session.get(search_url, headers=headers)
            response.raise_for_status()
            
            # Now perform the search
            search_data = {
                'q': query,
                'exact_match': 'false',
                'no_title_search': 'false'
            }
            
            response = session.post(search_url, headers=headers, data=search_data)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Extract search results
            result_items = soup.find_all('div', class_='song-result')
            for item in result_items[:max_results]:
                title_element = item.find('h3')
                artist_element = item.find('p', class_='artist')
                lyrics_element = item.find('div', class_='lyrics-snippet')
                
                if title_element and lyrics_element:
                    title = title_element.text.strip()
                    artist = artist_element.text.strip() if artist_element else "Unknown Artist"
                    lyrics = lyrics_element.text.strip()
                    
                    results.append({
                        "content": lyrics,
                        "source": f"{artist} - {title}",
                        "relevanceScore": 0.85
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Chosic for lyrics: {str(e)}")
            return []
    
    # Removed search_lyrics_fallback method as per requirements to only use external sources
    
    def search_lyrics(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for song lyrics using multiple external sources.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing song information
        """
        # Log the search attempt
        logger.info(f"Searching for lyrics with query: {query}")
        
        # Search using multiple external methods
        genius_results = self.search_lyrics_genius(query, max_results=max_results//3)
        logger.info(f"Genius search returned {len(genius_results)} results")
        
        google_results = self.search_lyrics_google(query, max_results=max_results//3)
        logger.info(f"Google search returned {len(google_results)} results")
        
        chosic_results = self.search_lyrics_chosic(query, max_results=max_results//3)
        logger.info(f"Chosic search returned {len(chosic_results)} results")
        
        # Combine results
        all_results = genius_results + google_results + chosic_results
        
        # Check if we have any results
        if not all_results:
            # Instead of raising an exception, try a more lenient search
            logger.warning(f"No lyrics found for query: {query}, trying more lenient search")
            
            # Try searching with a more general query by taking just the first word
            # or a substring of the original query
            simplified_query = query.split()[0] if ' ' in query else query[:min(len(query), 5)]
            
            if simplified_query != query:
                logger.info(f"Trying simplified query: {simplified_query}")
                
                # Try again with the simplified query
                genius_results = self.search_lyrics_genius(simplified_query, max_results=max_results//3)
                google_results = self.search_lyrics_google(simplified_query, max_results=max_results//3)
                chosic_results = self.search_lyrics_chosic(simplified_query, max_results=max_results//3)
                
                # Combine results
                all_results = genius_results + google_results + chosic_results
        
        # If we still have no results, return an empty list instead of raising an exception
        if not all_results:
            logger.error(f"No lyrics found for query: {query} or simplified query")
            return []
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x.get('relevanceScore', 0), reverse=True)
        
        # Return limited number of results
        return all_results[:max_results]
