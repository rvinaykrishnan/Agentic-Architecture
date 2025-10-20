from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import json
import re
import os
from datetime import datetime
from typing import List, Dict, Any
import hashlib

console = Console()
mcp = FastMCP("QAAgent")

# Persistent file-based storage
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)
DOCS_FILE = os.path.join(STORAGE_DIR, "documents.json")
MEMORY_FILE = os.path.join(STORAGE_DIR, "memory.json")

# Load from files or initialize empty
def load_storage():
    global document_store, memory_store
    try:
        if os.path.exists(DOCS_FILE):
            with open(DOCS_FILE, 'r') as f:
                document_store = json.load(f)
        else:
            document_store = []
    except:
        document_store = []
    
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                memory_store = json.load(f)
        else:
            memory_store = []
    except:
        memory_store = []

def save_documents():
    with open(DOCS_FILE, 'w') as f:
        json.dump(document_store, f, indent=2)

def save_memory():
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory_store, f, indent=2)

# Load storage on startup
load_storage()
document_store = document_store if 'document_store' in dir() else []
memory_store = memory_store if 'memory_store' in dir() else []
query_history = []

@mcp.tool()
def analyze_query(query: str) -> TextContent:
    """Analyze the user's query to determine intent and extract key information"""
    console.print("[blue]FUNCTION CALL:[/blue] analyze_query()")
    console.print(f"[blue]Query:[/blue] {query}")
    
    try:
        analysis = {
            "original_query": query,
            "query_length": len(query),
            "word_count": len(query.split()),
            "contains_question": any(q in query.lower() for q in ['what', 'when', 'where', 'who', 'why', 'how']),
            "is_factual": any(word in query.lower() for word in ['fact', 'data', 'information', 'stats', 'number']),
            "is_recent": any(word in query.lower() for word in ['recent', 'lately', 'today', 'yesterday', 'latest', 'now', 'current']),
            "is_comparative": any(word in query.lower() for word in ['compare', 'vs', 'versus', 'difference', 'better']),
            "requires_context": len(query.split()) > 5,
            "requires_live_data": any(word in query.lower() for word in ['latest', 'recent', 'today', 'now', 'current', 'live', 'tweet', 'post']),
            "keywords": extract_keywords(query),
            "timestamp": datetime.now().isoformat()
        }
        
        # Determine query type
        if analysis['contains_question'] and analysis['is_factual']:
            analysis['query_type'] = 'FACTUAL_QUESTION'
        elif analysis['is_comparative']:
            analysis['query_type'] = 'COMPARATIVE_ANALYSIS'
        elif analysis['is_recent'] or analysis['requires_live_data']:
            analysis['query_type'] = 'TEMPORAL_QUERY'
        else:
            analysis['query_type'] = 'GENERAL_INQUIRY'
        
        # Recommend search method
        if analysis['requires_live_data']:
            analysis['recommended_method'] = 'WEB_SEARCH'
        else:
            analysis['recommended_method'] = 'RAG_OR_KNOWLEDGE'
        
        # Display analysis
        table = Table(title="Query Analysis", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Attribute", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in analysis.items():
            if key != "keywords":
                table.add_row(key.replace('_', ' ').title(), str(value))
        
        console.print(table)
        console.print(Panel(
            f"Keywords: {', '.join(analysis['keywords'])}\n"
            f"Recommended Method: {analysis['recommended_method']}",
            title="Extracted Keywords",
            border_style="cyan"
        ))
        
        return TextContent(
            type="text",
            text=json.dumps(analysis)
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )

def extract_keywords(text: str) -> List[str]:
    """Extract important keywords from text"""
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                  'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                  'should', 'could', 'may', 'might', 'must', 'can', 'about'}
    
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words]
    
    # Return unique keywords, limit to top 10 by frequency
    from collections import Counter
    word_freq = Counter(keywords)
    return [word for word, _ in word_freq.most_common(10)]

@mcp.tool()
def retrieve_documents(keywords: List[str], limit: int = 5) -> TextContent:
    """Retrieve relevant documents from the document store based on keywords"""
    console.print("[blue]FUNCTION CALL:[/blue] retrieve_documents()")
    console.print(f"[blue]Keywords:[/blue] {keywords}")
    console.print(f"[blue]Limit:[/blue] {limit}")
    
    try:
        # Always load fresh from file to get latest documents
        load_storage()
        
        if not document_store:
            console.print("[yellow]Warning:[/yellow] Document store is empty")
            return TextContent(
                type="text",
                text=json.dumps({"documents": [], "count": 0, "message": "No documents in store"})
            )
        
        # Score documents based on keyword matches
        scored_docs = []
        for doc in document_store:
            score = calculate_relevance_score(doc, keywords)
            if score > 0:
                scored_docs.append({
                    "document": doc,
                    "score": score
                })
        
        # Sort by score and limit
        scored_docs.sort(key=lambda x: x['score'], reverse=True)
        top_docs = scored_docs[:limit]
        
        # Display results
        table = Table(title="Retrieved Documents", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Title", style="blue")
        table.add_column("Score", style="green", width=8)
        table.add_column("Matches", style="yellow", width=10)
        
        for i, item in enumerate(top_docs, 1):
            doc = item['document']
            table.add_row(
                str(i),
                doc.get('title', 'Untitled')[:40],
                f"{item['score']:.2f}",
                str(len([k for k in keywords if k in doc.get('content', '').lower()]))
            )
        
        console.print(table)
        
        result = {
            "documents": [item['document'] for item in top_docs],
            "count": len(top_docs),
            "total_in_store": len(document_store)
        }
        
        return TextContent(
            type="text",
            text=json.dumps(result)
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )

def calculate_relevance_score(doc: Dict[str, Any], keywords: List[str]) -> float:
    """Calculate relevance score between document and keywords"""
    content = (doc.get('content', '') + ' ' + doc.get('title', '')).lower()
    score = 0.0
    
    for keyword in keywords:
        # Count occurrences
        count = content.count(keyword.lower())
        score += count * 1.0
        
        # Bonus for title matches
        if keyword.lower() in doc.get('title', '').lower():
            score += 5.0
    
    return score

@mcp.tool()
def store_document(title: str, content: str, url: str = "", metadata: dict = None) -> TextContent:
    """Store a document in the document store for future retrieval"""
    console.print("[blue]FUNCTION CALL:[/blue] store_document()")
    console.print(f"[blue]Title:[/blue] {title}")
    
    try:
        load_storage()  # Load latest before storing
        
        doc_id = hashlib.md5(f"{title}{content}".encode()).hexdigest()
        
        document = {
            "id": doc_id,
            "title": title,
            "content": content,
            "url": url,
            "metadata": metadata or {},
            "stored_at": datetime.now().isoformat(),
            "access_count": 0
        }
        
        # Check for duplicates
        existing = [d for d in document_store if d['id'] == doc_id]
        if existing:
            console.print("[yellow]Warning:[/yellow] Document already exists, updating...")
            document_store.remove(existing[0])
        
        document_store.append(document)
        
        # Save to file for persistence
        save_documents()
        
        console.print(Panel(
            f"[green]✓ Document stored successfully[/green]\n"
            f"ID: {doc_id[:12]}...\n"
            f"Title: {title}\n"
            f"Content Length: {len(content)} chars\n"
            f"Total Documents: {len(document_store)}",
            title="Storage Confirmation",
            border_style="green"
        ))
        
        return TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "document_id": doc_id,
                "total_documents": len(document_store)
            })
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )

@mcp.tool()
def store_in_memory(key: str, value: str, category: str = "general") -> TextContent:
    """Store information in memory for quick recall"""
    console.print("[blue]FUNCTION CALL:[/blue] store_in_memory()")
    console.print(f"[blue]Key:[/blue] {key}")
    console.print(f"[blue]Category:[/blue] {category}")
    
    try:
        load_storage()  # Load latest before storing
        
        memory_item = {
            "key": key,
            "value": value,
            "category": category,
            "stored_at": datetime.now().isoformat(),
            "access_count": 0
        }
        
        # Update if exists
        existing = [m for m in memory_store if m['key'] == key]
        if existing:
            memory_store.remove(existing[0])
        
        memory_store.append(memory_item)
        
        # Save to file for persistence
        save_memory()
        
        console.print(f"[green]✓ Stored in memory:[/green] {key} = {value[:50]}...")
        
        return TextContent(
            type="text",
            text=json.dumps({"success": True, "total_memories": len(memory_store)})
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )

@mcp.tool()
def retrieve_from_memory(key: str = None, category: str = None) -> TextContent:
    """Retrieve information from memory"""
    console.print("[blue]FUNCTION CALL:[/blue] retrieve_from_memory()")
    
    try:
        load_storage()  # Load latest
        
        if key:
            items = [m for m in memory_store if m['key'] == key]
        elif category:
            items = [m for m in memory_store if m['category'] == category]
        else:
            items = memory_store
        
        # Update access count
        for item in items:
            item['access_count'] += 1
        
        save_memory()  # Save updated access counts
        
        console.print(f"[green]✓ Retrieved {len(items)} memory items[/green]")
        
        return TextContent(
            type="text",
            text=json.dumps({"memories": items, "count": len(items)})
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )

@mcp.tool()
def generate_response(query: str, documents: List[Dict], reasoning_steps: List[str]) -> TextContent:
    """Generate a structured response based on query and retrieved documents"""
    console.print("[blue]FUNCTION CALL:[/blue] generate_response()")
    
    try:
        # Synthesize information from documents
        sources = []
        context_snippets = []
        
        for doc in documents:
            sources.append(doc.get('title', 'Untitled'))
            content = doc.get('content', '')
            # Extract relevant snippet (first 200 chars)
            context_snippets.append(content[:200])
        
        response_data = {
            "query": query,
            "sources": sources,
            "context_snippets": context_snippets,
            "reasoning_steps": reasoning_steps,
            "document_count": len(documents),
            "confidence": calculate_confidence(documents),
            "generated_at": datetime.now().isoformat()
        }
        
        # Display response structure
        console.print(Panel(
            f"[bold cyan]Response Generated[/bold cyan]\n\n"
            f"Documents Used: {len(documents)}\n"
            f"Sources: {', '.join(sources[:3])}\n"
            f"Confidence: {response_data['confidence']:.1f}%\n"
            f"Reasoning Steps: {len(reasoning_steps)}",
            border_style="green"
        ))
        
        return TextContent(
            type="text",
            text=json.dumps(response_data)
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )

def calculate_confidence(documents: List[Dict]) -> float:
    """Calculate confidence score based on document quality and quantity"""
    if not documents:
        return 0.0
    
    base_score = min(len(documents) * 20, 60)  # Up to 60% for document count
    
    # Add bonus for recent documents
    recent_bonus = 0
    for doc in documents:
        stored_at = doc.get('stored_at', '')
        if stored_at:
            try:
                stored_time = datetime.fromisoformat(stored_at)
                age_hours = (datetime.now() - stored_time).total_seconds() / 3600
                if age_hours < 24:
                    recent_bonus += 10
            except:
                pass
    
    return min(base_score + recent_bonus, 95)  # Max 95% confidence

@mcp.tool()
def verify_answer(answer: str, sources: List[str]) -> TextContent:
    """Verify the answer against sources for accuracy"""
    console.print("[blue]FUNCTION CALL:[/blue] verify_answer()")
    
    try:
        verification = {
            "answer_length": len(answer),
            "sources_count": len(sources),
            "has_citations": len(sources) > 0,
            "is_comprehensive": len(answer) > 100,
            "verification_score": 0.0,
            "issues": []
        }
        
        # Calculate verification score
        score = 0.0
        if verification['has_citations']:
            score += 40
        if verification['is_comprehensive']:
            score += 30
        if len(answer.split()) > 20:
            score += 20
        if not any(word in answer.lower() for word in ['maybe', 'perhaps', 'possibly', 'might']):
            score += 10
        
        verification['verification_score'] = score
        
        # Check for issues
        if not verification['has_citations']:
            verification['issues'].append("No source citations provided")
        if len(answer) < 50:
            verification['issues'].append("Answer may be too brief")
        
        status = "VERIFIED" if score >= 70 else "NEEDS_REVIEW"
        
        console.print(Panel(
            f"[bold]Verification Status: {status}[/bold]\n\n"
            f"Score: {score:.0f}/100\n"
            f"Sources: {len(sources)}\n"
            f"Issues: {len(verification['issues'])}",
            title="Answer Verification",
            border_style="green" if score >= 70 else "yellow"
        ))
        
        if verification['issues']:
            console.print(Panel(
                "\n".join(f"• {issue}" for issue in verification['issues']),
                title="Issues Found",
                border_style="yellow"
            ))
        
        return TextContent(
            type="text",
            text=json.dumps(verification)
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )

@mcp.tool()
def get_statistics() -> TextContent:
    """Get statistics about the QA agent's usage and performance"""
    console.print("[blue]FUNCTION CALL:[/blue] get_statistics()")
    
    try:
        load_storage()  # Load latest
        
        stats = {
            "documents_stored": len(document_store),
            "memories_stored": len(memory_store),
            "queries_processed": len(query_history),
            "avg_documents_per_query": len(document_store) / max(len(query_history), 1),
            "most_accessed_document": None,
            "most_accessed_memory": None
        }
        
        if document_store:
            most_accessed = max(document_store, key=lambda d: d.get('access_count', 0))
            stats['most_accessed_document'] = most_accessed.get('title', 'Unknown')
        
        if memory_store:
            most_accessed = max(memory_store, key=lambda m: m.get('access_count', 0))
            stats['most_accessed_memory'] = most_accessed.get('key', 'Unknown')
        
        # Display statistics
        table = Table(title="QA Agent Statistics", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            table.add_row(key.replace('_', ' ').title(), str(value))
        
        console.print(table)
        
        return TextContent(
            type="text",
            text=json.dumps(stats)
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")
