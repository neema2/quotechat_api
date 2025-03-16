from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import time
from enum import Enum
from starlette.responses import Response
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import services
from app.services.search_service import SearchService, ContentType as ServiceContentType

app = FastAPI(title="QuoteChat API")

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add middleware to handle OPTIONS requests without authentication
@app.middleware("http")
async def options_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        # Return a response with CORS headers for preflight requests
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Max-Age"] = "86400"  # Cache preflight response for 24 hours
        return response
    
    # For non-OPTIONS requests, proceed with normal request handling
    return await call_next(request)

# Models
class ContentType(str, Enum):
    MOVIE_QUOTE = "Movie Quote"
    SONG_LYRIC = "Song Lyric"
    MEME = "Meme"

class Message(BaseModel):
    id: str
    content: str
    contentType: ContentType
    isFromCurrentUser: bool
    source: str
    timestamp: float

class Conversation(BaseModel):
    id: str
    name: str
    messages: List[Message] = []
    lastMessageTimestamp: Optional[float] = None

class SearchResult(BaseModel):
    id: str
    content: str
    contentType: ContentType
    source: str
    relevanceScore: float

# In-memory database
conversations: List[Conversation] = []

# Initialize services
search_service = SearchService(genius_token=os.environ.get("GENIUS_API_TOKEN"))

# Routes
@app.get("/")
def read_root():
    return {"message": "Welcome to QuoteChat API"}

@app.get("/conversations", response_model=List[Conversation])
def get_conversations():
    # Sort conversations by last message timestamp
    sorted_conversations = sorted(
        conversations, 
        key=lambda x: x.lastMessageTimestamp if x.lastMessageTimestamp else 0, 
        reverse=True
    )
    return sorted_conversations

@app.post("/conversations", response_model=Conversation)
def create_conversation(name: str):
    conversation_id = f"conv-{int(time.time())}"
    new_conversation = Conversation(id=conversation_id, name=name)
    conversations.append(new_conversation)
    return new_conversation

@app.get("/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: str):
    for conversation in conversations:
        if conversation.id == conversation_id:
            return conversation
    raise HTTPException(status_code=404, detail="Conversation not found")

@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    global conversations
    for i, conversation in enumerate(conversations):
        if conversation.id == conversation_id:
            conversations.pop(i)
            return {"message": "Conversation deleted"}
    raise HTTPException(status_code=404, detail="Conversation not found")

@app.post("/conversations/{conversation_id}/messages", response_model=Message)
def add_message(conversation_id: str, content: str, content_type: ContentType, source: str):
    for conversation in conversations:
        if conversation.id == conversation_id:
            message_id = f"msg-{int(time.time())}-{random.randint(1000, 9999)}"
            timestamp = time.time()
            
            # Create user message
            message = Message(
                id=message_id,
                content=content,
                contentType=content_type,
                isFromCurrentUser=True,
                source=source,
                timestamp=timestamp
            )
            conversation.messages.append(message)
            conversation.lastMessageTimestamp = timestamp
            
            # Generate automated response
            response_content = ""
            response_source = ""
            response_type = random.choice(list(ContentType))
            
            if response_type == ContentType.MOVIE_QUOTE:
                response = random.choice(movie_quotes)
                response_content = response["content"]
                response_source = response["source"]
            elif response_type == ContentType.SONG_LYRIC:
                response = random.choice(song_lyrics)
                response_content = response["content"]
                response_source = response["source"]
            else:
                response = random.choice(memes)
                response_content = response["content"]
                response_source = response["source"]
            
            # Add automated response
            response_id = f"msg-{int(time.time())}-{random.randint(1000, 9999)}"
            response_timestamp = time.time() + 1  # 1 second later
            
            response_message = Message(
                id=response_id,
                content=response_content,
                contentType=response_type,
                isFromCurrentUser=False,
                source=response_source,
                timestamp=response_timestamp
            )
            conversation.messages.append(response_message)
            conversation.lastMessageTimestamp = response_timestamp
            
            return message
            
    raise HTTPException(status_code=404, detail="Conversation not found")

@app.get("/search", response_model=List[SearchResult])
def search_content(query: str, content_type: ContentType):
    # Map API ContentType to service ContentType
    service_content_type = ServiceContentType(content_type.value)
    
    # Use enhanced search service
    search_results = search_service.search_content(query, service_content_type)
    
    # Convert to API response model
    results = []
    for i, item in enumerate(search_results):
        results.append(
            SearchResult(
                id=f"{content_type.value.lower().replace(' ', '-')}-{i}",
                content=item["content"],
                contentType=content_type,
                source=item["source"],
                relevanceScore=item.get("relevanceScore", 0.0)
            )
        )
    
    # Sort by relevance score
    results.sort(key=lambda x: x.relevanceScore, reverse=True)
    return results

@app.get("/popular", response_model=List[SearchResult])
def get_popular_content(content_type: ContentType):
    # Map API ContentType to service ContentType
    service_content_type = ServiceContentType(content_type.value)
    
    # Use enhanced search service for popular content
    popular_results = search_service.get_popular_content(service_content_type)
    
    # Convert to API response model
    results = []
    for i, item in enumerate(popular_results):
        results.append(
            SearchResult(
                id=f"{content_type.value.lower().replace(' ', '-')}-{i}",
                content=item["content"],
                contentType=content_type,
                source=item["source"],
                relevanceScore=item.get("relevanceScore", 1.0)
            )
        )
    
    return results

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Add some initial conversations for testing
@app.on_event("startup")
def startup_event():
    # Create a sample conversation
    conversation_id = "conv-sample"
    sample_conversation = Conversation(
        id=conversation_id,
        name="Sample Conversation",
        lastMessageTimestamp=time.time()
    )
    
    # Add some sample messages
    sample_conversation.messages = [
        Message(
            id="msg-1",
            content="I'll be back.",
            contentType=ContentType.MOVIE_QUOTE,
            isFromCurrentUser=True,
            source="Terminator",
            timestamp=time.time() - 3600
        ),
        Message(
            id="msg-2",
            content="Sweet dreams are made of this.",
            contentType=ContentType.SONG_LYRIC,
            isFromCurrentUser=False,
            source="Eurythmics - Sweet Dreams",
            timestamp=time.time() - 3500
        ),
        Message(
            id="msg-3",
            content="One does not simply walk into Mordor.",
            contentType=ContentType.MEME,
            isFromCurrentUser=True,
            source="Boromir Meme",
            timestamp=time.time() - 3400
        ),
        Message(
            id="msg-4",
            content="May the Force be with you.",
            contentType=ContentType.MOVIE_QUOTE,
            isFromCurrentUser=False,
            source="Star Wars",
            timestamp=time.time() - 3300
        )
    ]
    
    conversations.append(sample_conversation)

# Sample data for movie quotes
movie_quotes = [
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

# Sample data for song lyrics
song_lyrics = [
    {"content": "And I will always love you.", "source": "Whitney Houston - I Will Always Love You"},
    {"content": "Don't stop believin'.", "source": "Journey - Don't Stop Believin'"},
    {"content": "We will, we will rock you!", "source": "Queen - We Will Rock You"},
    {"content": "I'm on the highway to hell.", "source": "AC/DC - Highway to Hell"},
    {"content": "Imagine all the people living life in peace.", "source": "John Lennon - Imagine"},
    {"content": "I want to hold your hand.", "source": "The Beatles - I Want to Hold Your Hand"},
    {"content": "Like a rolling stone.", "source": "Bob Dylan - Like a Rolling Stone"},
    {"content": "Every breath you take, I'll be watching you.", "source": "The Police - Every Breath You Take"},
    {"content": "Sweet dreams are made of this.", "source": "Eurythmics - Sweet Dreams"},
    {"content": "I can't get no satisfaction.", "source": "The Rolling Stones - Satisfaction"},
]

# Sample data for memes
memes = [
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

# Fuzzy search function
def fuzzy_search(query: str, content_list: list, content_type: ContentType) -> List[SearchResult]:
    results = []
    query = query.lower()
    
    for i, item in enumerate(content_list):
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
            results.append(
                SearchResult(
                    id=f"{content_type.value.lower().replace(' ', '-')}-{i}",
                    content=item["content"],
                    contentType=content_type,
                    source=source,
                    relevanceScore=score
                )
            )
    
    # Sort by relevance score
    results.sort(key=lambda x: x.relevanceScore, reverse=True)
    return results
