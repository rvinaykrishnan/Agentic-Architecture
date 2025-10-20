"""
Demo Scenarios for Stakeholder Presentation
Showcases 5 different scenarios demonstrating RAG, Google Search, and Gemini Fallback
"""
import os
import asyncio
import json
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Import agents
from perception import PerceptionAgent, QueryInput, UserPreference
from memory import MemoryAgent, MemoryInput
from decision import DecisionAgent, DecisionInput
from action import ActionAgent, ActionInput
from flow_logger import FlowLogger

console = Console()

# Demo scenarios
DEMO_SCENARIOS = [
    {
        "id": 1,
        "name": "RAG Method - Technical Documentation",
        "description": "Query about stored technical content",
        "query": "What is quantum computing?",
        "setup": "Store quantum computing document first",
        "expected_method": "RAG",
        "user_preferences": {
            "expertise_level": "expert",
            "response_style": "detailed",
            "depth_preference": "deep",
            "focus_areas": ["quantum physics", "technology"],
            "preferred_sources": ["academic", "official docs"],
            "time_sensitivity": "low"
        },
        "documents_to_store": [
            {
                "title": "Introduction to Quantum Computing - Academic Paper",
                "content": """Quantum computing is a revolutionary computing paradigm that leverages the principles of quantum mechanics to process information. Unlike classical computers that use bits (0 or 1), quantum computers use quantum bits or qubits. Qubits can exist in superposition states, allowing them to represent multiple states simultaneously. This property, combined with quantum entanglement and interference, enables quantum computers to solve certain problems exponentially faster than classical computers. Key applications include cryptography, drug discovery, optimization problems, and simulating quantum systems. Major quantum algorithms include Shor's algorithm for factoring large numbers and Grover's algorithm for database search.""",
                "url": "https://academic.edu/quantum-computing-intro"
            },
            {
                "title": "Quantum Mechanics Fundamentals",
                "content": """Quantum mechanics is the fundamental theory describing the behavior of matter and energy at the atomic and subatomic scale. Key principles include wave-particle duality, uncertainty principle, superposition, and entanglement. These principles form the foundation for quantum computing technologies.""",
                "url": "https://physics.edu/quantum-mechanics"
            }
        ]
    },
    {
        "id": 2,
        "name": "Google Search Method - Current Events",
        "description": "Query requiring live/recent data",
        "query": "What are the latest developments in AI regulations in 2025?",
        "setup": "No documents stored - will use live search",
        "expected_method": "LIVE_SEARCH",
        "user_preferences": {
            "expertise_level": "intermediate",
            "response_style": "balanced",
            "depth_preference": "moderate",
            "focus_areas": ["AI", "policy", "regulations"],
            "preferred_sources": ["news", "official docs"],
            "time_sensitivity": "high"
        },
        "documents_to_store": []
    },
    {
        "id": 3,
        "name": "Gemini Fallback - General Knowledge",
        "description": "General knowledge question without RAG docs",
        "query": "How does photosynthesis work?",
        "setup": "No relevant documents - use Gemini knowledge",
        "expected_method": "GEMINI_KNOWLEDGE",
        "user_preferences": {
            "expertise_level": "beginner",
            "response_style": "concise",
            "depth_preference": "shallow",
            "focus_areas": ["biology", "science"],
            "preferred_sources": [],
            "time_sensitivity": "low"
        },
        "documents_to_store": []
    },
    {
        "id": 4,
        "name": "RAG Method - Company Knowledge Base",
        "description": "Query about internal company information",
        "query": "What is our company's AI ethics policy?",
        "setup": "Store company policy document",
        "expected_method": "RAG",
        "user_preferences": {
            "expertise_level": "intermediate",
            "response_style": "balanced",
            "depth_preference": "moderate",
            "focus_areas": ["business", "ethics", "AI"],
            "preferred_sources": ["official docs"],
            "time_sensitivity": "low"
        },
        "documents_to_store": [
            {
                "title": "Company AI Ethics Policy 2025",
                "content": """Our company's AI Ethics Policy establishes guidelines for responsible AI development and deployment. Key principles include: 1) Transparency - All AI systems must be explainable and auditable. 2) Fairness - AI must not discriminate based on protected characteristics. 3) Privacy - User data must be protected and used only with consent. 4) Accountability - Clear ownership and responsibility for AI decisions. 5) Safety - AI systems must be tested rigorously before deployment. 6) Human Oversight - Critical decisions require human review. All employees working with AI must complete ethics training annually. Violations are reported to the Ethics Committee.""",
                "url": "https://company.internal/policies/ai-ethics"
            }
        ]
    },
    {
        "id": 5,
        "name": "Google Search Method - Breaking News",
        "description": "Query about very recent events",
        "query": "What happened in the stock market today?",
        "setup": "Time-sensitive query requiring live data",
        "expected_method": "LIVE_SEARCH",
        "user_preferences": {
            "expertise_level": "expert",
            "response_style": "detailed",
            "depth_preference": "deep",
            "focus_areas": ["finance", "markets", "economics"],
            "preferred_sources": ["news"],
            "time_sensitivity": "high"
        },
        "documents_to_store": []
    }
]


class DemoRunner:
    """Runs demo scenarios and captures logs"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.demo_logs_dir = os.path.join(os.path.dirname(__file__), "demo_logs")
        os.makedirs(self.demo_logs_dir, exist_ok=True)
    
    async def setup_documents(self, documents: list):
        """Store documents for RAG"""
        if not documents:
            console.print("[yellow]No documents to store for this scenario[/yellow]")
            return
        
        console.print(f"[cyan]Setting up {len(documents)} document(s) for RAG...[/cyan]")
        
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
                
                for doc in documents:
                    await session.call_tool("store_document", arguments={
                        "title": doc["title"],
                        "content": doc["content"],
                        "url": doc["url"],
                        "metadata": {"type": "demo"}
                    })
                    console.print(f"[green]✓ Stored: {doc['title']}[/green]")
    
    async def run_scenario(self, scenario: dict):
        """Run a single demo scenario with complete logging"""
        console.print("\n" + "="*80)
        console.print(Panel(
            f"[bold cyan]SCENARIO {scenario['id']}: {scenario['name']}[/bold cyan]\n\n"
            f"[yellow]Description:[/yellow] {scenario['description']}\n"
            f"[yellow]Query:[/yellow] \"{scenario['query']}\"\n"
            f"[yellow]Expected Method:[/yellow] {scenario['expected_method']}\n"
            f"[yellow]Setup:[/yellow] {scenario['setup']}",
            title=f"Demo Scenario {scenario['id']}",
            border_style="cyan"
        ))
        
        # Create logger for this scenario
        logger = FlowLogger(log_dir=os.path.join(self.demo_logs_dir, f"scenario_{scenario['id']}"))
        
        # Setup documents if needed
        await self.setup_documents(scenario['documents_to_store'])
        
        # Create user preferences
        prefs = UserPreference(**scenario['user_preferences'])
        
        # Log user input
        logger.log_user_input(scenario['query'], prefs.model_dump())
        
        # Initialize agents
        perception_agent = PerceptionAgent(self.api_key, prefs)
        memory_agent = MemoryAgent()
        decision_agent = DecisionAgent(self.api_key)
        action_agent = ActionAgent(self.api_key)
        
        console.print("\n[bold magenta]Running Agentic Architecture Flow...[/bold magenta]")
        
        # STAGE 1: PERCEPTION
        console.print("\n[cyan]→ Stage 1: Perception[/cyan]")
        query_input = QueryInput(query=scenario['query'])
        logger.log_perception_input({"query": scenario['query'], "user_preferences": prefs.model_dump()})
        
        perception_output = perception_agent.understand_query(query_input)
        logger.log_perception_output(perception_output.model_dump())
        
        # STAGE 2: MEMORY
        console.print("[cyan]→ Stage 2: Memory[/cyan]")
        memory_input = MemoryInput(from_perception=perception_output)
        logger.log_memory_input({"from_perception": perception_output.model_dump()})
        
        memory_output = memory_agent.retrieve_context(memory_input)
        logger.log_memory_output(memory_output.model_dump())
        
        # STAGES 3 & 4: DECISION ↔ ACTION
        console.print("[cyan]→ Stage 3 & 4: Decision ↔ Action Loop[/cyan]")
        
        iteration = 0
        max_iterations = 3
        previous_actions = []
        final_action_output = None
        
        while iteration < max_iterations:
            iteration += 1
            console.print(f"[yellow]   Iteration {iteration}[/yellow]")
            
            # DECISION
            decision_input = DecisionInput(
                from_memory=memory_output,
                available_tools=decision_agent.available_tools,
                previous_actions=previous_actions
            )
            logger.log_decision_input({
                "from_memory": memory_output.model_dump(),
                "available_tools": [t.model_dump() for t in decision_agent.available_tools],
                "previous_actions": previous_actions
            }, iteration)
            
            decision_output = decision_agent.make_decision(decision_input)
            logger.log_decision_output(decision_output.model_dump(), iteration)
            
            # ACTION
            action_input = ActionInput(
                from_decision=decision_output,
                from_memory=memory_output
            )
            logger.log_action_input({
                "from_decision": decision_output.model_dump(),
                "from_memory": memory_output.model_dump()
            }, iteration)
            
            action_output = await action_agent.execute_actions(action_input)
            logger.log_action_output(action_output.model_dump(), iteration)
            
            # Track actions
            for tool_result in action_output.tool_results:
                previous_actions.append({
                    "tool_name": tool_result.tool_name,
                    "success": tool_result.success,
                    "result_summary": tool_result.result_summary
                })
            
            final_action_output = action_output
            
            if not action_output.needs_another_decision:
                console.print("[green]   ✓ Loop complete[/green]")
                break
        
        # Log final output
        final_response = {
            "query": scenario['query'],
            "answer": final_action_output.final_answer,
            "confidence": final_action_output.confidence,
            "sources": final_action_output.sources,
            "method": final_action_output.method,
            "reasoning_flow": {
                "perception": perception_output.reasoning_steps,
                "memory": memory_output.reasoning_steps,
                "decision": [d['reasoning_steps'] for d in decision_output.model_dump().get('reasoning_steps', [])],
                "action": final_action_output.reasoning_steps
            },
            "user_preferences_applied": final_action_output.user_preferences is not None
        }
        
        logger.log_final_output(final_response)
        
        # Display results
        self._display_results(scenario, final_action_output)
        
        # Get log file paths
        log_files = logger.get_log_files()
        console.print(f"\n[bold green]✓ Logs saved:[/bold green]")
        console.print(f"   Text Log: {log_files['text_log']}")
        console.print(f"   JSON Log: {log_files['json_log']}")
        
        return final_action_output
    
    def _display_results(self, scenario: dict, action_output):
        """Display scenario results"""
        
        # Check if expected method matches
        method_match = action_output.method == scenario['expected_method']
        
        table = Table(title=f"Scenario {scenario['id']} Results", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green" if method_match else "yellow")
        
        table.add_row("Expected Method", scenario['expected_method'])
        table.add_row("Actual Method", f"{action_output.method} {'✓' if method_match else '⚠'}")
        table.add_row("Confidence", f"{action_output.confidence}%")
        table.add_row("Sources", str(len(action_output.sources)))
        table.add_row("Preferences Applied", "✅ Yes" if action_output.user_preferences else "❌ No")
        
        console.print(table)
        
        console.print("\n[bold]Answer Preview:[/bold]")
        console.print(Panel(
            action_output.final_answer[:500] + ("..." if len(action_output.final_answer) > 500 else ""),
            border_style="green"
        ))
    
    async def run_all_scenarios(self):
        """Run all demo scenarios"""
        console.print(Panel(
            "[bold cyan]QA Agent - Stakeholder Demo[/bold cyan]\n\n"
            "Running 5 scenarios demonstrating:\n"
            "• RAG Method (using stored documents)\n"
            "• Google Search Method (live data)\n"
            "• Gemini Fallback (general knowledge)\n\n"
            "[yellow]Each scenario will generate detailed logs showing\n"
            "the complete architectural flow with evidence.[/yellow]",
            title="Demo Suite",
            border_style="cyan"
        ))
        
        results = []
        
        for scenario in DEMO_SCENARIOS:
            try:
                result = await self.run_scenario(scenario)
                results.append({
                    "scenario": scenario,
                    "result": result,
                    "success": True
                })
            except Exception as e:
                console.print(f"[red]❌ Error in scenario {scenario['id']}: {e}[/red]")
                results.append({
                    "scenario": scenario,
                    "result": None,
                    "success": False,
                    "error": str(e)
                })
        
        # Summary
        self._display_summary(results)
    
    def _display_summary(self, results: list):
        """Display summary of all scenarios"""
        console.print("\n" + "="*80)
        console.print(Panel(
            "[bold green]Demo Suite Complete![/bold green]",
            border_style="green"
        ))
        
        table = Table(title="Summary", box=box.ROUNDED)
        table.add_column("ID", style="cyan", width=4)
        table.add_column("Scenario", style="yellow")
        table.add_column("Expected", style="magenta")
        table.add_column("Actual", style="blue")
        table.add_column("Status", style="green")
        
        for r in results:
            if r['success']:
                scenario = r['scenario']
                result = r['result']
                match = "✓" if result.method == scenario['expected_method'] else "⚠"
                table.add_row(
                    str(scenario['id']),
                    scenario['name'],
                    scenario['expected_method'],
                    result.method,
                    f"{match} Success"
                )
            else:
                scenario = r['scenario']
                table.add_row(
                    str(scenario['id']),
                    scenario['name'],
                    scenario['expected_method'],
                    "Error",
                    "❌ Failed"
                )
        
        console.print(table)
        
        console.print(f"\n[bold cyan]📁 All logs saved in:[/bold cyan] {self.demo_logs_dir}")
        console.print("\n[bold yellow]Evidence Documentation:[/bold yellow]")
        console.print("   • Each scenario has its own log directory")
        console.print("   • Text logs show complete flow with evidence")
        console.print("   • JSON logs contain structured data")
        console.print("   • Logs prove user preferences flow through all stages")
        console.print("   • Logs demonstrate Decision→Action based on Memory/Perception")
        console.print("   • Logs show MCP tool execution by Action module")


async def main():
    """Main entry point for demo"""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if not api_key:
        console.print("[red]❌ Error: GEMINI_API_KEY not found![/red]")
        return
    
    runner = DemoRunner(api_key)
    await runner.run_all_scenarios()


if __name__ == "__main__":
    asyncio.run(main())

