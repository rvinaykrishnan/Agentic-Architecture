"""
API Server for QA Agent Chrome Extension - NEW AGENTIC ARCHITECTURE
Bridges the Chrome extension with the new 5-module agentic system:
Perception → Memory → Decision ↔ Action with User Preferences
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import uvicorn
from rich.console import Console
from rich.panel import Panel
import sys
import os

# Import new agentic architecture
from main import QAAgentOrchestrator, process_query_api
from perception import UserPreference
from memory import MemoryAgent

console = Console()

app = FastAPI(title="QA Agent API - Agentic", version="2.0.0")

# Enable CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extension origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class QuestionRequest(BaseModel):
    question: str
    user_preferences: Optional[Dict] = None
    conversation_history: Optional[List[Dict]] = None

class PageContentRequest(BaseModel):
    title: str
    url: str
    content: str
    timestamp: Optional[str] = None

class UserPreferenceRequest(BaseModel):
    """Request to set/update user preferences"""
    preferred_language: str = "English"
    expertise_level: str = "intermediate"
    response_style: str = "balanced"
    focus_areas: List[str] = []
    location: Optional[str] = None
    preferred_sources: List[str] = []
    time_sensitivity: str = "moderate"
    depth_preference: str = "moderate"

# Global state
total_queries = 0
successful_queries = 0
current_user_preferences = None  # Store user preferences
api_key = None

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "QA Agent API - Agentic Architecture",
        "version": "2.0.0",
        "status": "running",
        "architecture": "Perception → Memory → Decision ↔ Action",
        "features": [
            "User preference personalization",
            "Chain-of-Thought reasoning",
            "MCP tool integration",
            "RAG with live search fallback",
            "Multi-stage decision making"
        ],
        "endpoints": {
            "POST /ask": "Ask a question (with optional preferences)",
            "POST /preferences": "Set user preferences",
            "GET /preferences": "Get current user preferences",
            "POST /store": "Store webpage content",
            "GET /memory": "Get memory summary",
            "GET /stats": "Get usage statistics",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "qa-agent",
        "queries_processed": total_queries
    }

@app.post("/preferences")
async def set_preferences(request: UserPreferenceRequest):
    """
    Set user preferences for personalized responses
    
    Args:
        request: UserPreferenceRequest with user preferences
        
    Returns:
        Confirmation of preferences set
    """
    global current_user_preferences
    
    try:
        current_user_preferences = UserPreference(**request.model_dump())
        
        console.print(Panel(
            f"[bold green]✓ User Preferences Updated[/bold green]\n\n"
            f"Expertise: {current_user_preferences.expertise_level}\n"
            f"Style: {current_user_preferences.response_style}\n"
            f"Depth: {current_user_preferences.depth_preference}\n"
            f"Focus: {', '.join(current_user_preferences.focus_areas) if current_user_preferences.focus_areas else 'General'}",
            border_style="green"
        ))
        
        return {
            "success": True,
            "message": "User preferences updated successfully",
            "preferences": current_user_preferences.model_dump()
        }
        
    except Exception as e:
        console.print(f"[red]Error setting preferences: {e}[/red]")
        raise HTTPException(
            status_code=400,
            detail=f"Error setting preferences: {str(e)}"
        )

@app.get("/preferences")
async def get_preferences():
    """
    Get current user preferences
    
    Returns:
        Current user preferences or defaults
    """
    if current_user_preferences:
        return {
            "success": True,
            "preferences": current_user_preferences.model_dump()
        }
    else:
        return {
            "success": True,
            "preferences": UserPreference().model_dump(),
            "message": "Using default preferences"
        }

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """
    Process a question through the NEW AGENTIC ARCHITECTURE
    
    Flow: Perception → Memory → Decision ↔ Action
    
    Args:
        request: QuestionRequest with question, optional preferences, and conversation history
        
    Returns:
        Structured answer with reasoning, sources, confidence, and method
    """
    global total_queries, successful_queries, current_user_preferences, api_key
    
    try:
        console.print(Panel(
            f"[bold cyan]New Query (Agentic):[/bold cyan] {request.question}",
            border_style="cyan"
        ))
        
        total_queries += 1
        
        # Use preferences from request or global
        preferences_dict = request.user_preferences or (
            current_user_preferences.model_dump() if current_user_preferences else None
        )
        
        # Process query through new agentic architecture
        result = await process_query_api(
            query=request.question,
            api_key=api_key,
            user_preferences=preferences_dict,
            conversation_history=request.conversation_history
        )
        
        if result.get('confidence', 0) > 0:
            successful_queries += 1
        
        console.print(Panel(
            f"[green]✓ Query processed via AGENTIC ARCHITECTURE[/green]\n"
            f"Confidence: {result.get('confidence', 0)}%\n"
            f"Method: {result.get('method', 'UNKNOWN')}\n"
            f"Stages: Perception → Memory → Decision ↔ Action\n"
            f"Preferences Applied: {result.get('user_preferences_applied', False)}",
            border_style="green"
        ))
        
        return {
            "success": True,
            "answer": result.get('answer', 'No answer generated'),
            "confidence": result.get('confidence', 0),
            "sources": result.get('sources', []),
            "method": result.get('method', 'UNKNOWN'),
            "reasoning_flow": result.get('reasoning_flow', {}),
            "user_preferences_applied": result.get('user_preferences_applied', False),
            "architecture": "Perception → Memory → Decision ↔ Action"
        }
        
    except Exception as e:
        console.print(f"[red]Error processing question: {e}[/red]")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing question: {str(e)}"
        )

@app.post("/store")
async def store_content(request: PageContentRequest):
    """
    Store webpage content in the document store (uses MCP tools directly)
    
    Args:
        request: PageContentRequest with page details
        
    Returns:
        Success status and document count
    """
    try:
        console.print(Panel(
            f"[bold cyan]Storing Content:[/bold cyan]\n"
            f"Title: {request.title}\n"
            f"URL: {request.url}\n"
            f"Length: {len(request.content)} chars",
            border_style="cyan"
        ))
        
        # Use MCP tools directly for storage
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        import sys
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qa_tools_path = os.path.join(script_dir, "qa_tools.py")
        
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[qa_tools_path]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool("store_document", arguments={
                    "title": request.title,
                    "content": request.content,
                    "url": request.url,
                    "metadata": {"type": "webpage"}
                })
                
                import json
                data = json.loads(result.content[0].text)
                
                console.print(Panel(
                    f"[green]✓ Content stored successfully[/green]\n"
                    f"Total documents: {data.get('total_documents', 0)}",
                    border_style="green"
                ))
                
                return {
                    "success": data.get('success', True),
                    "message": f"Stored '{request.title}' successfully",
                    "total_documents": data.get('total_documents', 0)
                }
        
    except Exception as e:
        console.print(f"[red]Error storing content: {e}[/red]")
        raise HTTPException(
            status_code=500,
            detail=f"Error storing content: {str(e)}"
        )

@app.get("/memory")
async def get_memory():
    """
    Get summary of stored memories and conversation history
    
    Returns:
        Memory count, conversation count, and summary
    """
    try:
        memory_agent = MemoryAgent()
        
        # Load conversation history
        import json
        conv_file = os.path.join(memory_agent.storage_dir, "conversation_history.json")
        conv_count = 0
        if os.path.exists(conv_file):
            with open(conv_file, 'r') as f:
                conversations = json.load(f)
                conv_count = len(conversations)
        
        # Load memories
        mem_file = os.path.join(memory_agent.storage_dir, "memory.json")
        mem_count = 0
        if os.path.exists(mem_file):
            with open(mem_file, 'r') as f:
                memories = json.load(f)
                mem_count = len(memories)
        
        # Load documents
        doc_file = os.path.join(memory_agent.storage_dir, "documents.json")
        doc_count = 0
        if os.path.exists(doc_file):
            with open(doc_file, 'r') as f:
                documents = json.load(f)
                doc_count = len(documents)
        
        return {
            "success": True,
            "conversations": conv_count,
            "memories": mem_count,
            "documents": doc_count,
            "summary": f"{conv_count} conversations, {mem_count} memories, {doc_count} documents stored"
        }
        
    except Exception as e:
        console.print(f"[red]Error retrieving memory: {e}[/red]")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving memory: {str(e)}"
        )

@app.get("/stats")
async def get_statistics():
    """
    Get usage statistics from the agentic system
    
    Returns:
        Statistics about queries, documents, accuracy, and architecture info
    """
    try:
        memory_agent = MemoryAgent()
        
        # Load document count
        import json
        doc_file = os.path.join(memory_agent.storage_dir, "documents.json")
        doc_count = 0
        if os.path.exists(doc_file):
            with open(doc_file, 'r') as f:
                documents = json.load(f)
                doc_count = len(documents)
        
        # Calculate accuracy
        accuracy = 100
        if total_queries > 0:
            accuracy = int((successful_queries / total_queries) * 100)
        
        return {
            "success": True,
            "architecture": "Perception → Memory → Decision ↔ Action",
            "questions": total_queries,
            "successful_queries": successful_queries,
            "documents": doc_count,
            "accuracy": accuracy,
            "has_user_preferences": current_user_preferences is not None,
            "features": [
                "User preference personalization",
                "Chain-of-Thought reasoning",
                "Multi-stage decision making",
                "MCP tool integration"
            ]
        }
        
    except Exception as e:
        console.print(f"[red]Error retrieving stats: {e}[/red]")
        return {
            "success": True,
            "questions": total_queries,
            "successful_queries": successful_queries,
            "documents": 0,
            "accuracy": 100
        }

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    global api_key
    
    # Load API key
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if not api_key:
        console.print("[red]❌ WARNING: GEMINI_API_KEY not found in environment![/red]")
    
    console.print(Panel(
        "[bold green]🚀 QA Agent API Server Started - AGENTIC ARCHITECTURE[/bold green]\n\n"
        "[magenta]Architecture:[/magenta]\n"
        "  Perception → Memory → Decision ↔ Action\n\n"
        "[cyan]Endpoints:[/cyan]\n"
        "• POST http://localhost:8000/ask - Ask questions (with preferences)\n"
        "• POST http://localhost:8000/preferences - Set user preferences\n"
        "• GET  http://localhost:8000/preferences - Get preferences\n"
        "• POST http://localhost:8000/store - Store content\n"
        "• GET  http://localhost:8000/memory - View memory\n"
        "• GET  http://localhost:8000/stats - View statistics\n"
        "• GET  http://localhost:8000/health - Health check\n\n"
        "[yellow]✨ Features: User Preferences, CoT Reasoning, MCP Tools, RAG[/yellow]\n"
        "[yellow]Ready to receive requests from Chrome extension![/yellow]",
        title="QA Agent API v2.0 - Agentic",
        border_style="green"
    ))

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    console.print(Panel(
        f"[bold yellow]Shutting down...[/bold yellow]\n\n"
        f"Total queries processed: {total_queries}\n"
        f"Successful queries: {successful_queries}\n"
        f"Success rate: {(successful_queries/max(total_queries, 1))*100:.1f}%",
        title="Shutdown Summary",
        border_style="yellow"
    ))

def main():
    """Main entry point"""
    console.print(Panel(
        "[bold cyan]Starting QA Agent API Server - AGENTIC ARCHITECTURE[/bold cyan]\n\n"
        "[magenta]Architecture:[/magenta] Perception → Memory → Decision ↔ Action\n\n"
        "Make sure your Chrome extension is configured to use:\n"
        "[green]http://localhost:8000[/green]\n\n"
        "[yellow]New in v2.0:[/yellow]\n"
        "• User preference personalization\n"
        "• Chain-of-Thought reasoning at every stage\n"
        "• Multi-stage decision-action loop\n"
        "• Pydantic models for all inputs/outputs",
        border_style="cyan"
    ))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()

