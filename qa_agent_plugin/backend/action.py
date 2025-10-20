"""
Action Module - Executes tool calls based on decisions
Interacts with MCP tools and generates final responses
"""
import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from google.genai import types
from rich.console import Console

console = Console()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ActionInput(BaseModel):
    """Input to action module"""
    from_decision: Any  # DecisionOutput from decision.py
    from_memory: Any  # MemoryOutput from memory.py (for context)
    

class ToolResult(BaseModel):
    """Result from a single tool execution"""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    result_summary: str = Field(..., description="Brief summary of what happened")
    

class ActionOutput(BaseModel):
    """Output from action module"""
    tool_results: List[ToolResult] = Field(default_factory=list, description="Results from tool calls")
    final_answer: Optional[str] = Field(None, description="Final answer to user query")
    reasoning_steps: List[str] = Field(default_factory=list, description="Action reasoning steps")
    confidence: float = Field(..., ge=0, le=100, description="Confidence in final answer")
    sources: List[str] = Field(default_factory=list, description="Sources used")
    method: str = Field(..., description="Method used: RAG, LIVE_SEARCH, GEMINI_KNOWLEDGE")
    needs_another_decision: bool = Field(default=False, description="Whether to loop back to decision")
    user_preferences: Optional[Dict] = Field(None, description="User preferences maintained throughout")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tool_results": [
                    {
                        "tool_name": "retrieve_documents",
                        "success": True,
                        "result": {"documents": []},
                        "result_summary": "Retrieved 3 documents"
                    }
                ],
                "final_answer": "AI is artificial intelligence...",
                "reasoning_steps": ["Retrieved documents", "Generated answer"],
                "confidence": 85.0,
                "sources": ["Document 1", "Document 2"],
                "method": "RAG",
                "needs_another_decision": False
            }
        }


# ============================================================================
# ACTION AGENT CLASS
# ============================================================================

class ActionAgent:
    """
    Action Agent - Fourth stage of agentic architecture
    Executes tool calls and generates final responses with user preference integration
    """
    
    def __init__(self, api_key: str):
        """Initialize action agent with API key"""
        self.client = genai.Client(api_key=api_key)
        
    async def _execute_mcp_tool(self, session: ClientSession, tool_name: str, arguments: Dict) -> ToolResult:
        """Execute a single MCP tool call"""
        try:
            console.print(f"[yellow]→ Executing: {tool_name}[/yellow]")
            
            result = await session.call_tool(tool_name, arguments=arguments)
            result_data = json.loads(result.content[0].text)
            
            # Create summary based on tool
            if tool_name == "analyze_query":
                summary = f"Analyzed query, found {len(result_data.get('keywords', []))} keywords"
            elif tool_name == "retrieve_documents":
                doc_count = len(result_data.get('documents', []))
                summary = f"Retrieved {doc_count} relevant documents"
            elif tool_name == "store_document":
                summary = f"Stored document successfully"
            elif tool_name == "verify_answer":
                score = result_data.get('verification_score', 0)
                summary = f"Verification score: {score}/100"
            elif tool_name == "get_statistics":
                summary = f"Retrieved system statistics"
            else:
                summary = f"Executed {tool_name} successfully"
            
            console.print(f"[green]✓ {summary}[/green]")
            
            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result_data,
                result_summary=summary
            )
            
        except Exception as e:
            console.print(f"[red]❌ Error executing {tool_name}: {e}[/red]")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result={},
                error=str(e),
                result_summary=f"Failed: {str(e)}"
            )
    
    async def _generate_final_answer(
        self,
        query: str,
        memory_output: Any,
        tool_results: List[ToolResult],
        method: str
    ) -> tuple[str, List[str], float]:
        """
        Generate final answer incorporating user preferences
        
        Returns:
            (answer, sources, confidence)
        """
        try:
            console.print("[yellow]→ Generating final answer with user preferences...[/yellow]")
            
            # Extract user preferences
            user_prefs = memory_output.user_preferences or {}
            
            # Build preference-aware prompt
            preference_instructions = ""
            if user_prefs:
                preference_instructions = f"""
**CRITICAL - INCORPORATE THESE USER PREFERENCES IN YOUR ANSWER:**

- **Expertise Level:** {user_prefs.get('expertise_level', 'intermediate')}
  → Adjust technical depth and terminology accordingly
  
- **Response Style:** {user_prefs.get('response_style', 'balanced')}
  → If 'concise': Keep it brief and to the point
  → If 'balanced': Provide clear explanation with key details
  → If 'detailed': Provide comprehensive, in-depth explanation
  
- **Depth Preference:** {user_prefs.get('depth_preference', 'moderate')}
  → If 'shallow': High-level overview only
  → If 'moderate': Explain main concepts clearly
  → If 'deep': Explain underlying mechanisms and nuances
  
- **Focus Areas:** {', '.join(user_prefs.get('focus_areas', [])) if user_prefs.get('focus_areas') else 'General'}
  → Relate answer to these areas when possible
  
- **Preferred Sources:** {', '.join(user_prefs.get('preferred_sources', [])) if user_prefs.get('preferred_sources') else 'Any'}
  → Prioritize these types of sources if available

**IMPORTANT:** Your answer MUST reflect these preferences in tone, depth, and style!
"""
            
            # Determine method and build context
            if method == "RAG":
                # Find retrieved documents
                documents = []
                for result in tool_results:
                    if result.tool_name == "retrieve_documents" and result.success:
                        documents = result.result.get("documents", [])
                        break
                
                if documents:
                    # Build context from documents
                    context = "\n\n=== RETRIEVED DOCUMENTS ===\n"
                    sources = []
                    for i, doc in enumerate(documents, 1):
                        context += f"\nDocument {i}: {doc.get('title', 'Untitled')}\n"
                        context += f"Content: {doc.get('content', '')[:500]}...\n"
                        context += f"URL: {doc.get('url', 'N/A')}\n"
                        context += "-" * 50 + "\n"
                        sources.append(doc.get('title', 'Unknown'))
                    
                    prompt = f"""{preference_instructions}

{context}

**QUESTION:** {query}

**YOUR TASK:**
Based on the documents above, provide a clear and accurate answer that:
1. Directly addresses the user's question
2. Matches their expertise level and preferred style
3. Incorporates their depth preference
4. Cites specific information from the documents

**OUTPUT FORMAT:**
{{
  "answer": "Your preference-aligned answer here...",
  "confidence": 85,
  "sources_used": ["source1", "source2"]
}}

Respond ONLY with valid JSON:"""
                    
                    response = self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt
                    )
                    
                    response_text = response.text if response and response.text else "{}"
                    
                    # Parse response
                    if "```json" in response_text:
                        json_start = response_text.find("```json") + 7
                        json_end = response_text.find("```", json_start)
                        response_text = response_text[json_start:json_end].strip()
                    elif "```" in response_text:
                        json_start = response_text.find("```") + 3
                        json_end = response_text.find("```", json_start)
                        response_text = response_text[json_start:json_end].strip()
                    
                    result = json.loads(response_text)
                    return (
                        result.get("answer", response_text),
                        sources,
                        result.get("confidence", 85.0)
                    )
            
            elif method == "LIVE_SEARCH":
                # Use Google Search Grounding
                console.print("[cyan]🌐 Using Google Search Grounding for live data...[/cyan]")
                
                search_prompt = f"""{preference_instructions}

**QUESTION:** {query}

**YOUR TASK:**
Provide a current, accurate answer using live web search that:
1. Uses the most recent information available
2. Matches the user's expertise level ({user_prefs.get('expertise_level', 'intermediate')})
3. Follows their preferred response style ({user_prefs.get('response_style', 'balanced')})
4. Provides appropriate depth ({user_prefs.get('depth_preference', 'moderate')})

Answer the question directly and comprehensively:"""
                
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=search_prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        response_modalities=["TEXT"]
                    )
                )
                
                answer = response.text if response and response.text else "Could not retrieve live data"
                return (answer, ["Google Search (Live Web Data)"], 85.0)
            
            else:  # GEMINI_KNOWLEDGE
                console.print("[cyan]🧠 Using Gemini's general knowledge...[/cyan]")
                
                knowledge_prompt = f"""{preference_instructions}

**QUESTION:** {query}

**YOUR TASK:**
Provide a clear, accurate answer from your knowledge base that:
1. Directly addresses the question
2. Matches the user's expertise level ({user_prefs.get('expertise_level', 'intermediate')})
3. Follows their preferred response style ({user_prefs.get('response_style', 'balanced')})
4. Provides appropriate depth ({user_prefs.get('depth_preference', 'moderate')})
5. Relates to their focus areas when relevant: {', '.join(user_prefs.get('focus_areas', [])) if user_prefs.get('focus_areas') else 'General'}

**OUTPUT FORMAT:**
{{
  "answer": "Your preference-aligned answer here...",
  "confidence": 80
}}

Respond ONLY with valid JSON:"""
                
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=knowledge_prompt
                )
                
                response_text = response.text if response and response.text else "{}"
                
                # Parse response
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                try:
                    result = json.loads(response_text)
                    return (
                        result.get("answer", response_text),
                        ["Gemini AI Knowledge Base"],
                        result.get("confidence", 80.0)
                    )
                except:
                    return (response_text, ["Gemini AI Knowledge Base"], 75.0)
                    
        except Exception as e:
            console.print(f"[red]❌ Error generating answer: {e}[/red]")
            import traceback
            traceback.print_exc()
            return (f"Error generating answer: {str(e)}", [], 0.0)
    
    async def execute_actions(self, action_input: ActionInput) -> ActionOutput:
        """
        Execute all decided actions and generate final response
        
        Args:
            action_input: ActionInput with decision and memory
            
        Returns:
            ActionOutput with results and final answer
        """
        try:
            console.print("[bold cyan]⚡ ACTION: Executing tools...[/bold cyan]")
            
            decision = action_input.from_decision
            memory_output = action_input.from_memory
            tool_results = []
            reasoning_steps = []
            
            # Maintain user preferences throughout
            user_prefs = decision.user_preferences
            
            # Determine method
            method = memory_output.suggested_method
            if memory_output.requires_live_data:
                method = "LIVE_SEARCH"
            elif memory_output.has_sufficient_context:
                method = "RAG"
            else:
                method = "GEMINI_KNOWLEDGE"
            
            reasoning_steps.append(f"[METHOD_SELECT] Using {method} approach")
            
            # Execute tool calls if any
            if decision.should_call_tool and decision.tool_calls:
                # Get MCP server path
                script_dir = os.path.dirname(os.path.abspath(__file__))
                qa_tools_path = os.path.join(script_dir, "qa_tools.py")
                
                server_params = StdioServerParameters(
                    command=sys.executable,
                    args=[qa_tools_path]
                )
                
                # Execute tools
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        console.print("[green]✓ MCP Server connected[/green]")
                        
                        # Execute each tool in order
                        for tool_call in sorted(decision.tool_calls, key=lambda x: x.priority):
                            result = await self._execute_mcp_tool(
                                session,
                                tool_call.tool_name,
                                tool_call.arguments
                            )
                            tool_results.append(result)
                            reasoning_steps.append(f"[TOOL_EXEC] {result.result_summary}")
            
            # Generate final answer
            reasoning_steps.append("[ANSWER_GEN] Generating final answer with user preferences")
            
            final_answer, sources, confidence = await self._generate_final_answer(
                query=memory_output.original_query,
                memory_output=memory_output,
                tool_results=tool_results,
                method=method
            )
            
            # Verify answer if verify_answer tool was called
            for result in tool_results:
                if result.tool_name == "verify_answer" and result.success:
                    verify_score = result.result.get("verification_score", 0)
                    reasoning_steps.append(f"[VERIFICATION] Answer verified with score {verify_score}/100")
            
            reasoning_steps.append(f"[COMPLETE] Final answer generated with {confidence}% confidence")
            
            output = ActionOutput(
                tool_results=tool_results,
                final_answer=final_answer,
                reasoning_steps=reasoning_steps,
                confidence=confidence,
                sources=sources,
                method=method,
                needs_another_decision=False,
                user_preferences=user_prefs
            )
            
            console.print(f"[bold green]✓ Action complete![/bold green]")
            console.print(f"[cyan]  Method: {method}[/cyan]")
            console.print(f"[cyan]  Confidence: {confidence}%[/cyan]")
            console.print(f"[cyan]  Sources: {len(sources)}[/cyan]")
            
            return output
            
        except Exception as e:
            console.print(f"[red]❌ Error in action execution: {e}[/red]")
            import traceback
            traceback.print_exc()
            
            # Emergency fallback
            return ActionOutput(
                tool_results=[],
                final_answer=f"Error: {str(e)}",
                reasoning_steps=[f"[ERROR] {str(e)}"],
                confidence=0.0,
                sources=[],
                method="ERROR",
                needs_another_decision=False,
                user_preferences=None
            )


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    from perception import PerceptionAgent, QueryInput, UserPreference
    from memory import MemoryAgent, MemoryInput
    from decision import DecisionAgent, DecisionInput
    from dotenv import load_dotenv
    
    async def test():
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY", "")
        
        console.print("[bold magenta]Testing Action Module[/bold magenta]\n")
        
        # Create sample data flow
        preferences = UserPreference(
            preferred_language="English",
            expertise_level="expert",
            response_style="detailed",
            focus_areas=["technology", "AI", "machine learning"],
            depth_preference="deep"
        )
        
        # Full pipeline
        perception_agent = PerceptionAgent(api_key=api_key, user_preferences=preferences)
        query_input = QueryInput(query="What is neural network?")
        perception_output = perception_agent.understand_query(query_input)
        
        memory_agent = MemoryAgent()
        memory_input = MemoryInput(from_perception=perception_output)
        memory_output = memory_agent.retrieve_context(memory_input)
        
        decision_agent = DecisionAgent(api_key=api_key)
        decision_input = DecisionInput(from_memory=memory_output)
        decision_output = decision_agent.make_decision(decision_input)
        
        action_agent = ActionAgent(api_key=api_key)
        action_input = ActionInput(from_decision=decision_output, from_memory=memory_output)
        action_output = await action_agent.execute_actions(action_input)
        
        console.print(f"\n[bold green]Final Answer:[/bold green]")
        console.print(action_output.final_answer)
        console.print(f"\n[bold cyan]Method:[/bold cyan] {action_output.method}")
        console.print(f"[bold cyan]Confidence:[/bold cyan] {action_output.confidence}%")
        console.print(f"[bold cyan]Sources:[/bold cyan] {', '.join(action_output.sources)}")
    
    asyncio.run(test())

