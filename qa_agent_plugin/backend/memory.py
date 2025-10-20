"""
Memory Module - Manages conversation history, RAG context, and user preferences
Prepares enriched context for decision-making
"""
import os
import json
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from rich.console import Console

console = Console()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ConversationEntry(BaseModel):
    """Single conversation entry"""
    query: str
    answer: str
    timestamp: str
    method: str = Field(default="UNKNOWN", description="How answer was obtained: RAG, GEMINI_FALLBACK, GOOGLE_SEARCH")
    confidence: float = Field(default=0.0, ge=0, le=100)


class RAGDocument(BaseModel):
    """Document from RAG storage"""
    id: str
    title: str
    content: str
    url: Optional[str] = None
    relevance_score: float = Field(default=0.0, ge=0, le=100)
    stored_at: str
    access_count: int = Field(default=0)


class MemoryItem(BaseModel):
    """Item stored in agent memory"""
    key: str
    value: str
    category: str = Field(default="general")
    stored_at: str
    access_count: int = Field(default=0)


class MemoryInput(BaseModel):
    """Input to memory module"""
    from_perception: Any  # PerceptionOutput from perception.py
    conversation_history: List[ConversationEntry] = Field(default_factory=list)
    retrieved_documents: List[RAGDocument] = Field(default_factory=list)
    stored_memories: List[MemoryItem] = Field(default_factory=list)
    

class MemoryOutput(BaseModel):
    """Output from memory module - enriched context for decision-making"""
    original_query: str
    analyzed_intent: str
    query_type: str
    extracted_keywords: List[str]
    requires_live_data: bool
    requires_deep_reasoning: bool
    
    # User preferences (CRITICAL for personalization)
    user_preferences: Optional[Dict] = Field(None, description="User preferences for personalized responses")
    
    # Context from memory
    relevant_conversation: List[ConversationEntry] = Field(default_factory=list, description="Previous relevant conversations")
    relevant_documents: List[RAGDocument] = Field(default_factory=list, description="RAG documents matching query")
    relevant_memories: List[MemoryItem] = Field(default_factory=list, description="Agent memories related to query")
    
    # Enriched context
    context_summary: str = Field(..., description="Summary of all available context")
    has_sufficient_context: bool = Field(..., description="Whether we have enough context to answer")
    suggested_method: str = Field(..., description="Suggested method: RAG, LIVE_SEARCH, GEMINI_KNOWLEDGE")
    
    # Reasoning
    reasoning_steps: List[str] = Field(default_factory=list, description="Memory reasoning steps")
    confidence: float = Field(..., ge=0, le=100, description="Confidence in context quality")
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "What is quantum computing?",
                "analyzed_intent": "Understanding quantum computing concept",
                "query_type": "FACTUAL",
                "extracted_keywords": ["quantum", "computing"],
                "requires_live_data": False,
                "requires_deep_reasoning": False,
                "user_preferences": {"expertise_level": "intermediate"},
                "relevant_conversation": [],
                "relevant_documents": [],
                "relevant_memories": [],
                "context_summary": "No relevant documents found",
                "has_sufficient_context": False,
                "suggested_method": "GEMINI_KNOWLEDGE",
                "reasoning_steps": ["Checked RAG storage", "No documents found"],
                "confidence": 70.0
            }
        }


# ============================================================================
# MEMORY AGENT CLASS
# ============================================================================

class MemoryAgent:
    """
    Memory Agent - Second stage of agentic architecture
    Manages and retrieves relevant context from various sources
    """
    
    def __init__(self, storage_dir: str = None):
        """Initialize memory agent with storage directory"""
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(__file__), "storage")
        
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.docs_file = os.path.join(self.storage_dir, "documents.json")
        self.memory_file = os.path.join(self.storage_dir, "memory.json")
        self.conversation_file = os.path.join(self.storage_dir, "conversation_history.json")
        
    def _load_documents(self) -> List[RAGDocument]:
        """Load documents from storage"""
        try:
            if os.path.exists(self.docs_file):
                with open(self.docs_file, 'r') as f:
                    docs_data = json.load(f)
                    return [RAGDocument(**doc) for doc in docs_data]
        except Exception as e:
            console.print(f"[yellow]⚠️  Error loading documents: {e}[/yellow]")
        return []
    
    def _load_memories(self) -> List[MemoryItem]:
        """Load memories from storage"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    mem_data = json.load(f)
                    return [MemoryItem(**mem) for mem in mem_data]
        except Exception as e:
            console.print(f"[yellow]⚠️  Error loading memories: {e}[/yellow]")
        return []
    
    def _load_conversation_history(self) -> List[ConversationEntry]:
        """Load conversation history from storage"""
        try:
            if os.path.exists(self.conversation_file):
                with open(self.conversation_file, 'r') as f:
                    conv_data = json.load(f)
                    return [ConversationEntry(**entry) for entry in conv_data]
        except Exception as e:
            console.print(f"[yellow]⚠️  Error loading conversation: {e}[/yellow]")
        return []
    
    def _save_conversation_history(self, history: List[ConversationEntry]):
        """Save conversation history to storage"""
        try:
            with open(self.conversation_file, 'w') as f:
                json.dump([entry.model_dump() for entry in history], f, indent=2)
        except Exception as e:
            console.print(f"[red]❌ Error saving conversation: {e}[/red]")
    
    def _calculate_relevance(self, text: str, keywords: List[str]) -> float:
        """Calculate relevance score between text and keywords"""
        text_lower = text.lower()
        score = 0.0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            count = text_lower.count(keyword_lower)
            score += count * 10.0
        
        # Normalize to 0-100
        return min(score, 100.0)
    
    def retrieve_context(self, memory_input: MemoryInput) -> MemoryOutput:
        """
        Retrieve and prepare all relevant context for decision-making
        
        Args:
            memory_input: MemoryInput containing perception output and optional context
            
        Returns:
            MemoryOutput with enriched context
        """
        try:
            console.print("[bold cyan]💾 MEMORY: Retrieving context...[/bold cyan]")
            
            perception = memory_input.from_perception
            reasoning_steps = []
            
            # Extract user preferences from perception
            user_prefs = None
            if hasattr(perception, 'user_preferences') and perception.user_preferences:
                user_prefs = perception.user_preferences.model_dump()
                reasoning_steps.append("[PREFERENCE_LOAD] Loaded user preferences for personalization")
                console.print(f"[green]✓ User preferences loaded[/green]")
            
            # Step 1: Load all available data sources
            console.print("[yellow]→ Loading RAG documents...[/yellow]")
            all_documents = self._load_documents()
            reasoning_steps.append(f"[DATA_LOAD] Loaded {len(all_documents)} documents from RAG storage")
            
            console.print("[yellow]→ Loading agent memories...[/yellow]")
            all_memories = self._load_memories()
            reasoning_steps.append(f"[DATA_LOAD] Loaded {len(all_memories)} memory items")
            
            console.print("[yellow]→ Loading conversation history...[/yellow]")
            conversation_history = memory_input.conversation_history or self._load_conversation_history()
            reasoning_steps.append(f"[DATA_LOAD] Loaded {len(conversation_history)} previous conversations")
            
            # Step 2: Filter relevant documents based on keywords
            keywords = perception.extracted_keywords
            relevant_docs = []
            
            for doc in all_documents:
                # Calculate relevance
                title_score = self._calculate_relevance(doc.title, keywords)
                content_score = self._calculate_relevance(doc.content, keywords)
                combined_score = (title_score * 1.5 + content_score) / 2.5
                
                if combined_score > 10.0:  # Threshold for relevance
                    doc.relevance_score = combined_score
                    relevant_docs.append(doc)
            
            # Sort by relevance and take top 5
            relevant_docs.sort(key=lambda x: x.relevance_score, reverse=True)
            relevant_docs = relevant_docs[:5]
            
            reasoning_steps.append(f"[DOCUMENT_FILTER] Found {len(relevant_docs)} relevant documents (threshold: >10.0)")
            console.print(f"[green]✓ Found {len(relevant_docs)} relevant documents[/green]")
            
            # Step 3: Filter relevant memories
            relevant_memories = []
            for mem in all_memories:
                mem_score = self._calculate_relevance(mem.key + " " + mem.value, keywords)
                if mem_score > 5.0:
                    relevant_memories.append(mem)
            
            reasoning_steps.append(f"[MEMORY_FILTER] Found {len(relevant_memories)} relevant memories")
            
            # Step 4: Filter relevant conversation history (last 5 relevant)
            relevant_conversations = []
            for conv in conversation_history[-10:]:  # Check last 10
                conv_text = conv.query + " " + conv.answer
                conv_score = self._calculate_relevance(conv_text, keywords)
                if conv_score > 5.0:
                    relevant_conversations.append(conv)
            
            relevant_conversations = relevant_conversations[-5:]  # Keep last 5 relevant
            reasoning_steps.append(f"[CONVERSATION_FILTER] Found {len(relevant_conversations)} relevant past conversations")
            
            # Step 5: Determine if we have sufficient context
            has_sufficient_context = len(relevant_docs) > 0
            reasoning_steps.append(f"[CONTEXT_CHECK] Sufficient context: {has_sufficient_context}")
            
            # Step 6: Build context summary
            context_parts = []
            
            if relevant_docs:
                context_parts.append(f"{len(relevant_docs)} relevant documents available")
            else:
                context_parts.append("No relevant documents in RAG storage")
            
            if relevant_conversations:
                context_parts.append(f"{len(relevant_conversations)} related past conversations")
            
            if relevant_memories:
                context_parts.append(f"{len(relevant_memories)} agent memories")
            
            if user_prefs:
                context_parts.append(f"User preferences: {user_prefs.get('expertise_level', 'unknown')} level, {user_prefs.get('response_style', 'balanced')} style")
            
            context_summary = "; ".join(context_parts)
            reasoning_steps.append(f"[CONTEXT_SUMMARY] {context_summary}")
            
            # Step 7: Suggest method based on context
            if perception.requires_live_data:
                suggested_method = "LIVE_SEARCH"
                reasoning_steps.append("[METHOD_SUGGESTION] Live/current data required → LIVE_SEARCH")
            elif has_sufficient_context:
                suggested_method = "RAG"
                reasoning_steps.append("[METHOD_SUGGESTION] Sufficient documents found → RAG")
            else:
                suggested_method = "GEMINI_KNOWLEDGE"
                reasoning_steps.append("[METHOD_SUGGESTION] No relevant documents → GEMINI_KNOWLEDGE")
            
            # Step 8: Calculate confidence
            confidence = 50.0  # Base confidence
            if has_sufficient_context:
                confidence += 30.0
            if relevant_conversations:
                confidence += 10.0
            if user_prefs:
                confidence += 10.0  # Preferences help personalization
            
            confidence = min(confidence, 95.0)
            reasoning_steps.append(f"[CONFIDENCE_CALC] Final confidence: {confidence}%")
            
            # Create output
            output = MemoryOutput(
                original_query=perception.original_query,
                analyzed_intent=perception.analyzed_intent,
                query_type=perception.query_type,
                extracted_keywords=perception.extracted_keywords,
                requires_live_data=perception.requires_live_data,
                requires_deep_reasoning=perception.requires_deep_reasoning,
                user_preferences=user_prefs,
                relevant_conversation=relevant_conversations,
                relevant_documents=relevant_docs,
                relevant_memories=relevant_memories,
                context_summary=context_summary,
                has_sufficient_context=has_sufficient_context,
                suggested_method=suggested_method,
                reasoning_steps=reasoning_steps,
                confidence=confidence
            )
            
            console.print(f"[green]✓ Context prepared: {suggested_method} method suggested[/green]")
            console.print(f"[cyan]  Context: {context_summary}[/cyan]")
            
            return output
            
        except Exception as e:
            console.print(f"[red]❌ Error in memory retrieval: {e}[/red]")
            import traceback
            traceback.print_exc()
            
            # Emergency fallback
            return MemoryOutput(
                original_query=getattr(memory_input.from_perception, 'original_query', 'Unknown'),
                analyzed_intent=getattr(memory_input.from_perception, 'analyzed_intent', 'Unknown'),
                query_type=getattr(memory_input.from_perception, 'query_type', 'FACTUAL'),
                extracted_keywords=getattr(memory_input.from_perception, 'extracted_keywords', []),
                requires_live_data=getattr(memory_input.from_perception, 'requires_live_data', False),
                requires_deep_reasoning=getattr(memory_input.from_perception, 'requires_deep_reasoning', False),
                user_preferences=None,
                relevant_conversation=[],
                relevant_documents=[],
                relevant_memories=[],
                context_summary=f"Error: {str(e)}",
                has_sufficient_context=False,
                suggested_method="GEMINI_KNOWLEDGE",
                reasoning_steps=[f"[ERROR] {str(e)}"],
                confidence=0.0
            )
    
    def save_conversation(self, query: str, answer: str, method: str, confidence: float):
        """Save a conversation entry"""
        try:
            history = self._load_conversation_history()
            
            entry = ConversationEntry(
                query=query,
                answer=answer,
                timestamp=datetime.now().isoformat(),
                method=method,
                confidence=confidence
            )
            
            history.append(entry)
            
            # Keep only last 50 conversations
            if len(history) > 50:
                history = history[-50:]
            
            self._save_conversation_history(history)
            console.print("[green]✓ Conversation saved to memory[/green]")
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Error saving conversation: {e}[/yellow]")


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    from perception import PerceptionAgent, QueryInput, UserPreference
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    # Test with sample data
    console.print("[bold magenta]Testing Memory Module[/bold magenta]\n")
    
    # Create sample perception output
    preferences = UserPreference(
        preferred_language="English",
        expertise_level="intermediate",
        response_style="balanced",
        focus_areas=["technology", "AI"]
    )
    
    perception_agent = PerceptionAgent(api_key=api_key, user_preferences=preferences)
    query_input = QueryInput(query="What is machine learning?")
    perception_output = perception_agent.understand_query(query_input)
    
    # Test memory
    memory_agent = MemoryAgent()
    memory_input = MemoryInput(from_perception=perception_output)
    memory_output = memory_agent.retrieve_context(memory_input)
    
    console.print(f"\n[bold green]Memory Output:[/bold green]\n{memory_output.model_dump_json(indent=2)}")

