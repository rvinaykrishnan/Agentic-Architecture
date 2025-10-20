"""
Decision Module - Decides which tool to call based on perception and memory
Uses LLM-based reasoning to determine optimal tool sequence
"""
import os
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from google import genai
from rich.console import Console
import json

console = Console()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ToolDescription(BaseModel):
    """Description of an available MCP tool"""
    name: str
    description: str
    parameters: Dict[str, str]
    when_to_use: str
    

class DecisionInput(BaseModel):
    """Input to decision module"""
    from_memory: Any  # MemoryOutput from memory.py
    available_tools: List[ToolDescription] = Field(default_factory=list)
    previous_actions: List[Dict] = Field(default_factory=list, description="Actions taken so far in this session")
    

class ToolCall(BaseModel):
    """A single tool call decision"""
    tool_name: str
    arguments: Dict[str, Any]
    reasoning: str = Field(..., description="Why this tool was chosen")
    priority: int = Field(default=1, ge=1, le=10, description="Priority of this call (1=highest)")
    

class DecisionOutput(BaseModel):
    """Output from decision module"""
    should_call_tool: bool = Field(..., description="Whether to call a tool")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Ordered list of tools to call")
    reasoning_steps: List[str] = Field(..., description="Step-by-step decision reasoning")
    confidence: float = Field(..., ge=0, le=100, description="Confidence in decisions")
    needs_more_data: bool = Field(default=False, description="Whether more data is needed after these tools")
    final_answer_ready: bool = Field(default=False, description="Whether we can generate final answer after these tools")
    user_preferences: Optional[Dict] = Field(None, description="User preferences to maintain")
    
    class Config:
        json_schema_extra = {
            "example": {
                "should_call_tool": True,
                "tool_calls": [
                    {
                        "tool_name": "analyze_query",
                        "arguments": {"query": "What is AI?"},
                        "reasoning": "Need to analyze query structure",
                        "priority": 1
                    }
                ],
                "reasoning_steps": ["Analyzed context", "Selected appropriate tool"],
                "confidence": 85.0,
                "needs_more_data": False,
                "final_answer_ready": True
            }
        }


# ============================================================================
# DECISION AGENT CLASS
# ============================================================================

class DecisionAgent:
    """
    Decision Agent - Third stage of agentic architecture
    Decides which MCP tools to call based on context and goals
    """
    
    def __init__(self, api_key: str):
        """Initialize decision agent with API key"""
        self.client = genai.Client(api_key=api_key)
        
        # Define available MCP tools
        self.available_tools = [
            ToolDescription(
                name="analyze_query",
                description="Analyze query to extract intent, keywords, and metadata",
                parameters={"query": "string - the user's question"},
                when_to_use="First step: Always use to understand query structure and extract keywords"
            ),
            ToolDescription(
                name="retrieve_documents",
                description="Search RAG storage for relevant documents using keywords",
                parameters={"keywords": "list[string] - search keywords", "limit": "int - max documents to retrieve"},
                when_to_use="When you need to find stored information; use after analyze_query"
            ),
            ToolDescription(
                name="store_document",
                description="Store a new document in RAG storage",
                parameters={"title": "string", "content": "string", "url": "string", "metadata": "dict"},
                when_to_use="When user wants to save content or after capturing a webpage"
            ),
            ToolDescription(
                name="generate_response",
                description="Generate structured response using documents and reasoning",
                parameters={"query": "string", "documents": "list[dict]", "reasoning_steps": "list[string]"},
                when_to_use="After retrieving documents; synthesizes information into answer"
            ),
            ToolDescription(
                name="verify_answer",
                description="Verify answer quality and accuracy against sources",
                parameters={"answer": "string", "sources": "list[string]"},
                when_to_use="Final step: Verify the generated answer before returning to user"
            ),
            ToolDescription(
                name="store_in_memory",
                description="Store key-value pair in agent memory for quick recall",
                parameters={"key": "string", "value": "string", "category": "string"},
                when_to_use="To remember important facts or Q&A pairs for future reference"
            ),
            ToolDescription(
                name="retrieve_from_memory",
                description="Retrieve stored memories by key or category",
                parameters={"key": "string (optional)", "category": "string (optional)"},
                when_to_use="When query references past information or needs context"
            ),
            ToolDescription(
                name="get_statistics",
                description="Get usage statistics about the agent",
                parameters={},
                when_to_use="When user asks about system performance or usage stats"
            )
        ]
    
    def _build_decision_prompt(self, memory_output: Any, previous_actions: List[Dict]) -> str:
        """Build prompt for decision-making"""
        
        # Extract user preferences
        user_prefs_text = ""
        if memory_output.user_preferences:
            prefs = memory_output.user_preferences
            user_prefs_text = f"""
**USER PREFERENCES (MUST CONSIDER IN ALL DECISIONS):**
- Expertise Level: {prefs.get('expertise_level', 'intermediate')}
- Response Style: {prefs.get('response_style', 'balanced')}
- Focus Areas: {', '.join(prefs.get('focus_areas', [])) if prefs.get('focus_areas') else 'General'}
- Time Sensitivity: {prefs.get('time_sensitivity', 'moderate')}
- Depth Preference: {prefs.get('depth_preference', 'moderate')}
- Preferred Sources: {', '.join(prefs.get('preferred_sources', [])) if prefs.get('preferred_sources') else 'Any'}

IMPORTANT: Ensure your tool choices align with user preferences!
"""
        
        # Build available tools description
        tools_desc = "\n".join([
            f"{i+1}. **{tool.name}**\n"
            f"   Description: {tool.description}\n"
            f"   Parameters: {', '.join([f'{k}={v}' for k, v in tool.parameters.items()])}\n"
            f"   When to use: {tool.when_to_use}\n"
            for i, tool in enumerate(self.available_tools)
        ])
        
        # Build previous actions summary
        prev_actions_text = ""
        if previous_actions:
            prev_actions_text = "\n**PREVIOUS ACTIONS IN THIS SESSION:**\n"
            for i, action in enumerate(previous_actions, 1):
                prev_actions_text += f"{i}. Called {action.get('tool_name', 'unknown')} - {action.get('result_summary', 'completed')}\n"
        
        return f"""You are the DECISION module of an intelligent QA Agent system.

{user_prefs_text}

**YOUR ROLE:** Decide which tools to call to best answer the user's query.

**CONTEXT:**
- Query: {memory_output.original_query}
- Intent: {memory_output.analyzed_intent}
- Query Type: {memory_output.query_type}
- Keywords: {', '.join(memory_output.extracted_keywords)}
- Requires Live Data: {memory_output.requires_live_data}
- Suggested Method: {memory_output.suggested_method}
- Available Context: {memory_output.context_summary}
- Has Sufficient Context: {memory_output.has_sufficient_context}
- Relevant Documents: {len(memory_output.relevant_documents)}
- Relevant Conversations: {len(memory_output.relevant_conversation)}

{prev_actions_text}

**AVAILABLE MCP TOOLS:**
{tools_desc}

**DECISION-MAKING PROCESS (Think step-by-step):**

Step 1: [GOAL_ANALYSIS] What is the end goal?
   - Understand what the user ultimately wants
   - Consider their preferences and expertise level

Step 2: [CONTEXT_ASSESSMENT] What do we already have?
   - Review available documents, memories, conversations
   - Identify gaps in information

Step 3: [METHOD_SELECTION] Which approach is best?
   - RAG: If we have sufficient relevant documents
   - LIVE_SEARCH: If query needs current/real-time data
   - GEMINI_KNOWLEDGE: If it's general knowledge
   - Consider user's time sensitivity and preferred sources

Step 4: [TOOL_SEQUENCE] What tools do we need?
   - List tools in execution order
   - Explain why each tool is necessary
   - Consider dependencies between tools

Step 5: [PREFERENCE_ALIGNMENT] Do choices match user preferences?
   - Verify tool selection aligns with user's expertise level
   - Ensure response depth matches preference
   - Check if sources align with preferences

Step 6: [DECISION_VERIFICATION] Is this the optimal plan?
   - Self-check: Will these tools get us the answer?
   - Self-check: Are we calling unnecessary tools?
   - Self-check: Are we considering user preferences?

**COMMON PATTERNS:**

Pattern A: RAG Answer (we have documents)
1. retrieve_documents → Get relevant docs
2. generate_response → Create answer from docs
3. verify_answer → Check quality

Pattern B: Live Search (need current data)
1. Skip tools, let Action module use Google Search Grounding
2. verify_answer → Check quality after

Pattern C: General Knowledge (no docs, no live data needed)
1. Skip retrieval tools
2. generate_response → Use Gemini knowledge
3. verify_answer → Check quality

Pattern D: Store Content (user wants to save something)
1. store_document → Save the content
2. get_statistics → Show updated stats

**OUTPUT FORMAT (MANDATORY JSON):**
```json
{{
  "should_call_tool": true/false,
  "tool_calls": [
    {{
      "tool_name": "tool_name_here",
      "arguments": {{"param1": "value1", "param2": "value2"}},
      "reasoning": "Why this tool is needed",
      "priority": 1
    }}
  ],
  "reasoning_steps": [
    "[GOAL_ANALYSIS] explanation",
    "[CONTEXT_ASSESSMENT] explanation",
    "[METHOD_SELECTION] explanation",
    "[TOOL_SEQUENCE] explanation",
    "[PREFERENCE_ALIGNMENT] explanation",
    "[DECISION_VERIFICATION] explanation"
  ],
  "confidence": 85,
  "needs_more_data": false,
  "final_answer_ready": true
}}
```

**CRITICAL RULES:**
1. ALWAYS include reasoning_type tags in reasoning_steps
2. ALWAYS consider user preferences in your decisions
3. If has_sufficient_context=true and relevant_documents>0, prefer RAG pattern
4. If requires_live_data=true, prefer live search pattern
5. Don't call tools unnecessarily - be efficient
6. Order matters - analyze before retrieve, retrieve before generate
7. NEVER output anything except valid JSON

Now decide which tools to call:"""

    def make_decision(self, decision_input: DecisionInput) -> DecisionOutput:
        """
        Make decision about which tools to call
        
        Args:
            decision_input: DecisionInput with memory output and context
            
        Returns:
            DecisionOutput with tool calls and reasoning
        """
        try:
            console.print("[bold cyan]🤔 DECISION: Analyzing options...[/bold cyan]")
            
            memory_output = decision_input.from_memory
            previous_actions = decision_input.previous_actions
            
            # Build decision prompt
            prompt = self._build_decision_prompt(memory_output, previous_actions)
            
            # Call Gemini for decision
            console.print("[yellow]→ Calling Gemini for tool selection...[/yellow]")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            response_text = response.text if response and response.text else "{}"
            
            # Parse JSON response
            try:
                # Extract JSON from markdown code blocks if present
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                decision_data = json.loads(response_text)
                
                # Create ToolCall objects
                tool_calls = []
                for tc in decision_data.get("tool_calls", []):
                    tool_calls.append(ToolCall(
                        tool_name=tc.get("tool_name", "unknown"),
                        arguments=tc.get("arguments", {}),
                        reasoning=tc.get("reasoning", "No reasoning provided"),
                        priority=tc.get("priority", 1)
                    ))
                
                # Create output
                output = DecisionOutput(
                    should_call_tool=decision_data.get("should_call_tool", len(tool_calls) > 0),
                    tool_calls=tool_calls,
                    reasoning_steps=decision_data.get("reasoning_steps", []),
                    confidence=decision_data.get("confidence", 70.0),
                    needs_more_data=decision_data.get("needs_more_data", False),
                    final_answer_ready=decision_data.get("final_answer_ready", True),
                    user_preferences=memory_output.user_preferences
                )
                
                console.print(f"[green]✓ Decision made: {len(tool_calls)} tool(s) to call[/green]")
                for tc in tool_calls:
                    console.print(f"[cyan]  • {tc.tool_name}[/cyan]")
                
                return output
                
            except json.JSONDecodeError as e:
                console.print(f"[yellow]⚠️  JSON parsing failed, using fallback decision[/yellow]")
                
                # Fallback: Use suggested method from memory
                tool_calls = []
                reasoning_steps = ["[FALLBACK] Using memory-suggested method"]
                
                if memory_output.suggested_method == "RAG" and memory_output.has_sufficient_context:
                    # RAG pattern
                    tool_calls = [
                        ToolCall(
                            tool_name="retrieve_documents",
                            arguments={
                                "keywords": memory_output.extracted_keywords,
                                "limit": 5
                            },
                            reasoning="[FALLBACK] Using RAG based on available documents",
                            priority=1
                        ),
                        ToolCall(
                            tool_name="verify_answer",
                            arguments={
                                "answer": "to_be_generated",
                                "sources": []
                            },
                            reasoning="[FALLBACK] Verify answer quality",
                            priority=2
                        )
                    ]
                    reasoning_steps.append("[FALLBACK] Selected RAG pattern")
                else:
                    # No specific tools needed - will use Gemini directly
                    reasoning_steps.append("[FALLBACK] Will use Gemini knowledge directly")
                
                return DecisionOutput(
                    should_call_tool=len(tool_calls) > 0,
                    tool_calls=tool_calls,
                    reasoning_steps=reasoning_steps,
                    confidence=60.0,
                    needs_more_data=False,
                    final_answer_ready=True,
                    user_preferences=memory_output.user_preferences
                )
                
        except Exception as e:
            console.print(f"[red]❌ Error in decision-making: {e}[/red]")
            import traceback
            traceback.print_exc()
            
            # Emergency fallback - minimal decision
            return DecisionOutput(
                should_call_tool=False,
                tool_calls=[],
                reasoning_steps=[f"[ERROR] {str(e)}"],
                confidence=0.0,
                needs_more_data=False,
                final_answer_ready=True,
                user_preferences=None
            )


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    from perception import PerceptionAgent, QueryInput, UserPreference
    from memory import MemoryAgent, MemoryInput
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    console.print("[bold magenta]Testing Decision Module[/bold magenta]\n")
    
    # Create sample data flow
    preferences = UserPreference(
        preferred_language="English",
        expertise_level="intermediate",
        response_style="detailed",
        focus_areas=["technology", "AI"]
    )
    
    # Perception
    perception_agent = PerceptionAgent(api_key=api_key, user_preferences=preferences)
    query_input = QueryInput(query="What is deep learning?")
    perception_output = perception_agent.understand_query(query_input)
    
    # Memory
    memory_agent = MemoryAgent()
    memory_input = MemoryInput(from_perception=perception_output)
    memory_output = memory_agent.retrieve_context(memory_input)
    
    # Decision
    decision_agent = DecisionAgent(api_key=api_key)
    decision_input = DecisionInput(from_memory=memory_output)
    decision_output = decision_agent.make_decision(decision_input)
    
    console.print(f"\n[bold green]Decision Output:[/bold green]\n{decision_output.model_dump_json(indent=2)}")

