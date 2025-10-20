"""
Main Orchestrator - Coordinates the entire agentic architecture
Manages: Perception → Memory → Decision ↔ Action loop with user preferences
"""
import os
import asyncio
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box
from dotenv import load_dotenv

# Import all agent modules
from perception import PerceptionAgent, QueryInput, UserPreference, PerceptionOutput
from memory import MemoryAgent, MemoryInput, MemoryOutput
from decision import DecisionAgent, DecisionInput, DecisionOutput
from action import ActionAgent, ActionInput, ActionOutput
from flow_logger import FlowLogger, reset_flow_logger

console = Console()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class AgentResponse(BaseModel):
    """Final response from the agentic system"""
    query: str
    answer: str
    confidence: float = Field(..., ge=0, le=100)
    sources: List[str] = Field(default_factory=list)
    method: str
    reasoning_flow: Dict = Field(..., description="Complete reasoning from all stages")
    user_preferences_applied: bool = Field(..., description="Whether user preferences were used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is AI?",
                "answer": "Artificial Intelligence is...",
                "confidence": 85.0,
                "sources": ["Source 1", "Source 2"],
                "method": "RAG",
                "reasoning_flow": {
                    "perception": ["step1", "step2"],
                    "memory": ["step1", "step2"],
                    "decision": ["step1", "step2"],
                    "action": ["step1", "step2"]
                },
                "user_preferences_applied": True
            }
        }


# ============================================================================
# USER PREFERENCE COLLECTION
# ============================================================================

def collect_user_preferences(interactive: bool = True) -> UserPreference:
    """
    Collect user preferences before starting agentic flow
    This ensures personalized responses throughout the session
    """
    if not interactive:
        # Use defaults for non-interactive mode
        return UserPreference()
    
    try:
        console.print(Panel(
            "[bold cyan]🎯 Welcome to QA Agent with Personalization![/bold cyan]\n\n"
            "Before we begin, let's understand your preferences to provide\n"
            "the most relevant and personalized answers for you.",
            title="Preference Setup",
            border_style="cyan"
        ))
        # 1. Expertise Level
        console.print("\n[bold]1. What is your expertise level?[/bold]")
        console.print("   • beginner: New to most topics, need simple explanations")
        console.print("   • intermediate: Have some background, understand technical terms")
        console.print("   • expert: Deep knowledge, prefer detailed technical explanations")
        
        expertise = Prompt.ask(
            "Your expertise level",
            choices=["beginner", "intermediate", "expert"],
            default="intermediate"
        )
        
        # 2. Response Style
        console.print("\n[bold]2. What response style do you prefer?[/bold]")
        console.print("   • concise: Brief, to-the-point answers")
        console.print("   • balanced: Clear explanations with key details")
        console.print("   • detailed: Comprehensive, in-depth explanations")
        
        style = Prompt.ask(
            "Your response style",
            choices=["concise", "balanced", "detailed"],
            default="balanced"
        )
        
        # 3. Depth Preference
        console.print("\n[bold]3. How deep should explanations go?[/bold]")
        console.print("   • shallow: High-level overview only")
        console.print("   • moderate: Main concepts explained clearly")
        console.print("   • deep: Underlying mechanisms and nuances")
        
        depth = Prompt.ask(
            "Your depth preference",
            choices=["shallow", "moderate", "deep"],
            default="moderate"
        )
        
        # 4. Focus Areas
        console.print("\n[bold]4. What are your main areas of interest?[/bold]")
        console.print("   (e.g., technology, science, business, health, AI, etc.)")
        console.print("   Enter comma-separated topics or press Enter to skip")
        
        focus_input = Prompt.ask("Your focus areas", default="")
        focus_areas = [f.strip() for f in focus_input.split(",")] if focus_input else []
        
        # 5. Location (for context-aware responses)
        console.print("\n[bold]5. Your location (optional)[/bold]")
        console.print("   This helps provide context-relevant information")
        console.print("   (e.g., San Francisco, USA or London, UK)")
        
        location = Prompt.ask("Your location", default="")
        location = location if location else None
        
        # 6. Preferred Sources
        console.print("\n[bold]6. What types of sources do you prefer?[/bold]")
        console.print("   • academic: Research papers, scholarly articles")
        console.print("   • news: News articles, current events")
        console.print("   • blogs: Technical blogs, opinion pieces")
        console.print("   • official docs: Official documentation, whitepapers")
        console.print("   Enter comma-separated choices or press Enter for all")
        
        sources_input = Prompt.ask("Your preferred sources", default="")
        preferred_sources = [s.strip() for s in sources_input.split(",")] if sources_input else []
        
        # 7. Time Sensitivity
        console.print("\n[bold]7. How important is timeliness of information?[/bold]")
        console.print("   • low: Established knowledge is fine")
        console.print("   • moderate: Recent information preferred")
        console.print("   • high: Need latest/real-time information")
        
        time_sensitivity = Prompt.ask(
            "Time sensitivity",
            choices=["low", "moderate", "high"],
            default="moderate"
        )
        
        # Create preference object
        preferences = UserPreference(
            preferred_language="English",  # Default for now
            expertise_level=expertise,
            response_style=style,
            focus_areas=focus_areas,
            location=location,
            preferred_sources=preferred_sources,
            time_sensitivity=time_sensitivity,
            depth_preference=depth
        )
        
        # Show summary
        console.print("\n" + "="*60)
        console.print(Panel(
            f"[bold green]✓ Preferences Saved![/bold green]\n\n"
            f"Expertise: {preferences.expertise_level}\n"
            f"Style: {preferences.response_style}\n"
            f"Depth: {preferences.depth_preference}\n"
            f"Focus: {', '.join(preferences.focus_areas) if preferences.focus_areas else 'General'}\n"
            f"Location: {preferences.location or 'Not specified'}\n"
            f"Sources: {', '.join(preferences.preferred_sources) if preferences.preferred_sources else 'Any'}\n"
            f"Time Sensitivity: {preferences.time_sensitivity}\n\n"
            f"[cyan]These preferences will personalize all your answers![/cyan]",
            title="Your Personalization Profile",
            border_style="green"
        ))
        
        return preferences
        
    except (KeyboardInterrupt, EOFError, OSError):
        # Handle interactive prompt failures gracefully
        console.print("\n[yellow]Using default preferences...[/yellow]")
        return UserPreference()
    except Exception as e:
        console.print(f"\n[red]Error collecting preferences: {e}[/red]")
        console.print("[yellow]Using default preferences...[/yellow]")
        return UserPreference()


# ============================================================================
# MAIN ORCHESTRATOR CLASS
# ============================================================================

class QAAgentOrchestrator:
    """
    Main orchestrator that coordinates all agent modules
    Implements: Perception → Memory (once) → Decision ↔ Action (loop)
    """
    
    def __init__(self, api_key: str, user_preferences: Optional[UserPreference] = None):
        """Initialize orchestrator with API key and user preferences"""
        self.api_key = api_key
        self.user_preferences = user_preferences
        
        # Initialize all agents
        self.perception_agent = PerceptionAgent(api_key, user_preferences)
        self.memory_agent = MemoryAgent()
        self.decision_agent = DecisionAgent(api_key)
        self.action_agent = ActionAgent(api_key)
        
        console.print("[bold green]✓ All agent modules initialized[/bold green]")
    
    async def process_query(self, query: str, conversation_history: List[Dict] = None) -> AgentResponse:
        """
        Process a query through the complete agentic architecture
        
        Flow:
        1. PERCEPTION (once) - Understand query
        2. MEMORY (once) - Gather context
        3. DECISION ↔ ACTION (loop) - Decide and execute until complete
        
        Args:
            query: User's question
            conversation_history: Optional previous conversation context
            
        Returns:
            AgentResponse with final answer and reasoning
        """
        try:
            # Initialize flow logger for this query
            logger = reset_flow_logger()
            
            # Log user input
            user_prefs_dict = self.user_preferences.model_dump() if self.user_preferences else None
            logger.log_user_input(query, user_prefs_dict)
            
            console.print(Panel(
                f"[bold cyan]Processing Query:[/bold cyan] {query}",
                border_style="cyan"
            ))
            
            reasoning_flow = {}
            conversation_history = conversation_history or []
            
            # ================================================================
            # STAGE 1: PERCEPTION (Run Once)
            # ================================================================
            console.print("\n[bold magenta]┌─ STAGE 1: PERCEPTION ─┐[/bold magenta]")
            
            query_input = QueryInput(
                query=query,
                conversation_history=conversation_history
            )
            
            # Log perception input
            logger.log_perception_input({
                "query": query,
                "conversation_history": conversation_history,
                "user_preferences": user_prefs_dict
            })
            
            perception_output: PerceptionOutput = self.perception_agent.understand_query(query_input)
            reasoning_flow["perception"] = perception_output.reasoning_steps
            
            # Log perception output
            logger.log_perception_output(perception_output.model_dump())
            
            console.print("[bold magenta]└─ PERCEPTION COMPLETE ─┘[/bold magenta]\n")
            
            # ================================================================
            # STAGE 2: MEMORY (Run Once)
            # ================================================================
            console.print("[bold blue]┌─ STAGE 2: MEMORY ─┐[/bold blue]")
            
            memory_input = MemoryInput(
                from_perception=perception_output,
                conversation_history=conversation_history
            )
            
            # Log memory input
            logger.log_memory_input({"from_perception": perception_output.model_dump()})
            
            memory_output: MemoryOutput = self.memory_agent.retrieve_context(memory_input)
            reasoning_flow["memory"] = memory_output.reasoning_steps
            
            # Log memory output
            logger.log_memory_output(memory_output.model_dump())
            
            console.print("[bold blue]└─ MEMORY COMPLETE ─┘[/bold blue]\n")
            
            # ================================================================
            # STAGE 3 & 4: DECISION ↔ ACTION (Loop)
            # ================================================================
            console.print("[bold yellow]┌─ STAGE 3 & 4: DECISION ↔ ACTION LOOP ─┐[/bold yellow]")
            
            max_iterations = 3  # Prevent infinite loops
            iteration = 0
            previous_actions = []
            final_action_output = None
            
            while iteration < max_iterations:
                iteration += 1
                console.print(f"\n[bold]→ Iteration {iteration}[/bold]")
                
                # --- DECISION ---
                console.print(f"[yellow]  [Decision {iteration}][/yellow]")
                decision_input = DecisionInput(
                    from_memory=memory_output,
                    available_tools=self.decision_agent.available_tools,
                    previous_actions=previous_actions
                )
                
                # Log decision input
                logger.log_decision_input({
                    "from_memory": memory_output.model_dump(),
                    "available_tools": [t.model_dump() for t in self.decision_agent.available_tools],
                    "previous_actions": previous_actions
                }, iteration)
                
                decision_output: DecisionOutput = self.decision_agent.make_decision(decision_input)
                
                # Log decision output
                logger.log_decision_output(decision_output.model_dump(), iteration)
                
                if f"decision_{iteration}" not in reasoning_flow:
                    reasoning_flow[f"decision_{iteration}"] = []
                reasoning_flow[f"decision_{iteration}"].extend(decision_output.reasoning_steps)
                
                # --- ACTION ---
                console.print(f"[green]  [Action {iteration}][/green]")
                action_input = ActionInput(
                    from_decision=decision_output,
                    from_memory=memory_output
                )
                
                # Log action input
                logger.log_action_input({
                    "from_decision": decision_output.model_dump(),
                    "from_memory": memory_output.model_dump()
                }, iteration)
                
                action_output: ActionOutput = await self.action_agent.execute_actions(action_input)
                
                # Log action output
                logger.log_action_output(action_output.model_dump(), iteration)
                
                if f"action_{iteration}" not in reasoning_flow:
                    reasoning_flow[f"action_{iteration}"] = []
                reasoning_flow[f"action_{iteration}"].extend(action_output.reasoning_steps)
                
                # Track actions for next iteration
                for tool_result in action_output.tool_results:
                    previous_actions.append({
                        "tool_name": tool_result.tool_name,
                        "success": tool_result.success,
                        "result_summary": tool_result.result_summary
                    })
                
                final_action_output = action_output
                
                # Check if we should continue looping
                if not action_output.needs_another_decision:
                    console.print("[bold green]  ✓ Final answer ready, exiting loop[/bold green]")
                    break
                
                console.print("[yellow]  ↻ More actions needed, continuing loop...[/yellow]")
            
            console.print("[bold yellow]└─ DECISION ↔ ACTION LOOP COMPLETE ─┘[/bold yellow]\n")
            
            # ================================================================
            # CREATE FINAL RESPONSE
            # ================================================================
            if not final_action_output or not final_action_output.final_answer:
                raise Exception("No final answer generated")
            
            # Save conversation to memory
            self.memory_agent.save_conversation(
                query=query,
                answer=final_action_output.final_answer,
                method=final_action_output.method,
                confidence=final_action_output.confidence
            )
            
            # Build response
            response = AgentResponse(
                query=query,
                answer=final_action_output.final_answer,
                confidence=final_action_output.confidence,
                sources=final_action_output.sources,
                method=final_action_output.method,
                reasoning_flow=reasoning_flow,
                user_preferences_applied=self.user_preferences is not None
            )
            
            # Log final output
            logger.log_final_output(response.model_dump())
            
            # Get log file paths and print them
            log_files = logger.get_log_files()
            console.print(f"[bold green]📁 Logs saved:[/bold green]")
            console.print(f"   Text: {log_files['text_log']}")
            console.print(f"   JSON: {log_files['json_log']}")
            
            # Display final result (skip if not interactive)
            try:
                self._display_result(response)
            except (EOFError, OSError):
                # Skip display in non-interactive mode (API)
                pass
            
            return response
            
        except Exception as e:
            console.print(f"[red]❌ Error in orchestrator: {e}[/red]")
            import traceback
            traceback.print_exc()
            
            # Return error response
            return AgentResponse(
                query=query,
                answer=f"Error processing query: {str(e)}",
                confidence=0.0,
                sources=[],
                method="ERROR",
                reasoning_flow={"error": [str(e)]},
                user_preferences_applied=False
            )
    
    def _display_result(self, response: AgentResponse):
        """Display the final result in a nice format"""
        
        # Create result panel
        result_text = f"[bold green]Answer:[/bold green]\n{response.answer}\n\n"
        result_text += f"[bold cyan]Confidence:[/bold cyan] {response.confidence}%\n"
        result_text += f"[bold cyan]Method:[/bold cyan] {response.method}\n"
        result_text += f"[bold cyan]Sources:[/bold cyan] {len(response.sources)}\n"
        
        if response.sources:
            result_text += "\n[bold yellow]Sources Used:[/bold yellow]\n"
            for i, source in enumerate(response.sources, 1):
                result_text += f"  {i}. {source}\n"
        
        if response.user_preferences_applied:
            result_text += "\n[bold magenta]✓ Personalized based on your preferences[/bold magenta]"
        
        console.print("\n" + "="*70)
        console.print(Panel(result_text, title="[bold]Final Result[/bold]", border_style="green"))
        
        # Show reasoning flow summary (skip in non-interactive mode)
        try:
            if Confirm.ask("\nShow detailed reasoning flow?", default=False):
                table = Table(title="Reasoning Flow", box=box.ROUNDED)
                table.add_column("Stage", style="cyan")
                table.add_column("Steps", style="yellow")
                
                for stage, steps in response.reasoning_flow.items():
                    table.add_row(stage, "\n".join(steps[:3]) + ("..." if len(steps) > 3 else ""))
                
                console.print(table)
        except (EOFError, OSError):
            # Skip interactive prompt in API/non-interactive mode
            pass


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point for the QA Agent"""
    
    # Load environment
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if not api_key:
        console.print("[red]❌ Error: GEMINI_API_KEY not found in environment[/red]")
        return
    
    console.print(Panel(
        "[bold cyan]QA Agent - Agentic Architecture[/bold cyan]\n\n"
        "Architecture: Perception → Memory → Decision ↔ Action\n"
        "Features: User preferences, Chain-of-Thought, MCP tools, RAG",
        title="Welcome",
        border_style="cyan"
    ))
    
    # ========================================================================
    # CRITICAL: Collect user preferences BEFORE starting agentic flow
    # ========================================================================
    user_preferences = collect_user_preferences(interactive=True)
    
    # Initialize orchestrator with preferences
    orchestrator = QAAgentOrchestrator(api_key, user_preferences)
    
    console.print("\n[bold green]✓ System ready! Ask me anything.[/bold green]\n")
    
    # Interactive query loop
    conversation_history = []
    
    while True:
        try:
            # Get user query
            query = Prompt.ask("\n[bold cyan]Your question[/bold cyan] (or 'quit' to exit)")
            
            if query.lower() in ['quit', 'exit', 'q']:
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if not query.strip():
                continue
            
            # Process query
            response = await orchestrator.process_query(query, conversation_history)
            
            # Add to history
            conversation_history.append({
                "query": query,
                "answer": response.answer,
                "method": response.method,
                "confidence": response.confidence
            })
            
            # Keep only last 10 conversations
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]
            
        except (KeyboardInterrupt, EOFError, OSError):
            console.print("\n[yellow]Interrupted. Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


# ============================================================================
# PROGRAMMATIC API (for integration with other systems)
# ============================================================================

async def process_query_api(
    query: str,
    api_key: str,
    user_preferences: Optional[Dict] = None,
    conversation_history: Optional[List[Dict]] = None
) -> Dict:
    """
    Programmatic API for processing queries
    
    Args:
        query: User's question
        api_key: Gemini API key
        user_preferences: Optional dict of user preferences
        conversation_history: Optional conversation history
        
    Returns:
        Dict with answer, confidence, sources, method, etc.
    """
    try:
        # Create UserPreference from dict if provided
        prefs = None
        if user_preferences:
            prefs = UserPreference(**user_preferences)
        
        # Create orchestrator
        orchestrator = QAAgentOrchestrator(api_key, prefs)
        
        # Process query
        response = await orchestrator.process_query(query, conversation_history)
        
        # Return as dict
        return response.model_dump()
        
    except Exception as e:
        return {
            "query": query,
            "answer": f"Error: {str(e)}",
            "confidence": 0.0,
            "sources": [],
            "method": "ERROR",
            "reasoning_flow": {},
            "user_preferences_applied": False
        }


if __name__ == "__main__":
    asyncio.run(main())

