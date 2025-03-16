from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import time
import logging
from enum import Enum
from starlette.responses import Response
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            
            # Generate automated response using enhanced search services
            response_type = random.choice(list(ContentType))
            service_content_type = ServiceContentType(response_type.value)
            
            try:
                # Get popular content for the selected type as response
                popular_results = search_service.get_popular_content(service_content_type)
                
                if popular_results:
                    # Select a random result from the popular content
                    response = random.choice(popular_results)
                    response_content = response["content"]
                    response_source = response["source"]
                else:
                    # Fallback if no results found
                    response_content = f"I couldn't find any {response_type.value.lower()} to respond with."
                    response_source = "System"
            except Exception as e:
                logger.error(f"Error generating automated response: {str(e)}")
                response_content = "Sorry, I couldn't generate a response at this time."
                response_source = "System"
            
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
    try:
        # Map API ContentType to service ContentType
        service_content_type = ServiceContentType(content_type.value)
        
        # Use enhanced search service
        search_results = search_service.search_content(query, service_content_type)
        
        # If no results were found, log a warning but don't raise an exception
        if not search_results:
            logger.warning(f"No results found for {content_type.value} with query: {query}")
            return []
        
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
    except Exception as e:
        # Log the error
        logger.error(f"Error searching for {content_type.value}: {str(e)}")
        # Return a proper HTTP error response
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/popular", response_model=List[SearchResult])
def get_popular_content(content_type: ContentType):
    try:
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
    except Exception as e:
        # Log the error
        logger.error(f"Error getting popular content for {content_type.value}: {str(e)}")
        # Return a proper HTTP error response
        raise HTTPException(status_code=404, detail=str(e))

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

# Static lists and fuzzy search function removed as they're no longer needed
# The application now uses external search services for all content
