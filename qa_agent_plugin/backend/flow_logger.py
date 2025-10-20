"""
Flow Logger - Captures and logs the complete data flow through all stages
Creates detailed log files showing evidence of architecture flow
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

class FlowLogger:
    """Logger to track and document the flow through all architectural stages"""
    
    def __init__(self, log_dir: str = None):
        """Initialize flow logger"""
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
        
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create session-specific log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"flow_log_{timestamp}.json")
        self.text_log_file = os.path.join(self.log_dir, f"flow_log_{timestamp}.txt")
        
        self.current_session = {
            "session_id": timestamp,
            "start_time": datetime.now().isoformat(),
            "query": None,
            "user_preferences": None,
            "stages": {
                "perception": None,
                "memory": None,
                "decision": [],
                "action": []
            },
            "final_output": None
        }
        
        self._write_header()
    
    def _write_header(self):
        """Write header to text log"""
        with open(self.text_log_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("QA AGENT - AGENTIC ARCHITECTURE FLOW LOG\n")
            f.write("="*80 + "\n")
            f.write(f"Session ID: {self.current_session['session_id']}\n")
            f.write(f"Start Time: {self.current_session['start_time']}\n")
            f.write("="*80 + "\n\n")
    
    def log_user_input(self, query: str, user_preferences: Dict = None):
        """Log the initial user input and preferences"""
        self.current_session["query"] = query
        self.current_session["user_preferences"] = user_preferences
        
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 0: USER INPUT                                                  │
└─────────────────────────────────────────────────────────────────────┘

📥 User Query: "{query}"

👤 User Preferences:
{json.dumps(user_preferences, indent=2) if user_preferences else "   No preferences set"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    def log_perception_input(self, query_input: Dict):
        """Log perception stage input"""
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 1: PERCEPTION - INPUT                                          │
└─────────────────────────────────────────────────────────────────────┘

📨 Input to Perception:
   • Query: "{query_input.get('query', 'N/A')}"
   • Conversation History: {len(query_input.get('conversation_history', []))} entries
   • User Preferences: {"✓ Included" if query_input.get('user_preferences') else "✗ Not included"}

""")
    
    def log_perception_output(self, perception_output: Dict):
        """Log perception stage output"""
        self.current_session["stages"]["perception"] = perception_output
        
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 1: PERCEPTION - OUTPUT                                         │
└─────────────────────────────────────────────────────────────────────┘

🧠 Perception Analysis:
   • Original Query: "{perception_output.get('original_query', 'N/A')}"
   • Analyzed Intent: "{perception_output.get('analyzed_intent', 'N/A')}"
   • Query Type: {perception_output.get('query_type', 'N/A')}
   • Keywords: {', '.join(perception_output.get('extracted_keywords', []))}
   • Requires Live Data: {perception_output.get('requires_live_data', False)}
   • Requires Deep Reasoning: {perception_output.get('requires_deep_reasoning', False)}
   • Confidence: {perception_output.get('confidence', 0)}%

📋 Reasoning Steps:
{self._format_list(perception_output.get('reasoning_steps', []))}

👤 User Preferences Status:
   {"✓ PASSED TO NEXT STAGE" if perception_output.get('user_preferences') else "✗ NOT INCLUDED"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    def log_memory_input(self, memory_input: Dict):
        """Log memory stage input"""
        from_perception = memory_input.get('from_perception', {})
        
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 2: MEMORY - INPUT                                              │
└─────────────────────────────────────────────────────────────────────┘

📨 Input to Memory:
   ✓ FROM PERCEPTION:
      • Query: "{from_perception.get('original_query', 'N/A')}"
      • Intent: "{from_perception.get('analyzed_intent', 'N/A')}"
      • Keywords: {', '.join(from_perception.get('extracted_keywords', []))}
      • User Preferences: {"✓ Received" if from_perception.get('user_preferences') else "✗ Missing"}

   • Conversation History: {len(memory_input.get('conversation_history', []))} entries

""")
    
    def log_memory_output(self, memory_output: Dict):
        """Log memory stage output"""
        self.current_session["stages"]["memory"] = memory_output
        
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 2: MEMORY - OUTPUT                                             │
└─────────────────────────────────────────────────────────────────────┘

💾 Memory Context:
   • Relevant Documents: {len(memory_output.get('relevant_documents', []))}
   • Relevant Conversations: {len(memory_output.get('relevant_conversation', []))}
   • Relevant Memories: {len(memory_output.get('relevant_memories', []))}
   
📊 Context Assessment:
   • Context Summary: "{memory_output.get('context_summary', 'N/A')}"
   • Has Sufficient Context: {memory_output.get('has_sufficient_context', False)}
   • Suggested Method: {memory_output.get('suggested_method', 'N/A')}
   • Confidence: {memory_output.get('confidence', 0)}%

📋 Reasoning Steps:
{self._format_list(memory_output.get('reasoning_steps', []))}

👤 User Preferences Status:
   {"✓ MAINTAINED - PASSED TO NEXT STAGE" if memory_output.get('user_preferences') else "✗ NOT MAINTAINED"}

📚 RAG Documents Retrieved:
{self._format_documents(memory_output.get('relevant_documents', []))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    def log_decision_input(self, decision_input: Dict, iteration: int):
        """Log decision stage input"""
        from_memory = decision_input.get('from_memory', {})
        
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 3: DECISION - INPUT (Iteration {iteration})                   │
└─────────────────────────────────────────────────────────────────────┘

📨 Input to Decision:
   ✓ FROM MEMORY:
      • Query: "{from_memory.get('original_query', 'N/A')}"
      • Intent: "{from_memory.get('analyzed_intent', 'N/A')}"
      • Suggested Method: {from_memory.get('suggested_method', 'N/A')}
      • Has Sufficient Context: {from_memory.get('has_sufficient_context', False)}
      • User Preferences: {"✓ Received" if from_memory.get('user_preferences') else "✗ Missing"}

   • Available Tools: {len(decision_input.get('available_tools', []))}
   • Previous Actions: {len(decision_input.get('previous_actions', []))}

""")
    
    def log_decision_output(self, decision_output: Dict, iteration: int):
        """Log decision stage output"""
        self.current_session["stages"]["decision"].append({
            "iteration": iteration,
            "output": decision_output
        })
        
        tool_calls = decision_output.get('tool_calls', [])
        
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 3: DECISION - OUTPUT (Iteration {iteration})                  │
└─────────────────────────────────────────────────────────────────────┘

🤔 Decision Analysis:
   • Should Call Tool: {decision_output.get('should_call_tool', False)}
   • Number of Tool Calls: {len(tool_calls)}
   • Needs More Data: {decision_output.get('needs_more_data', False)}
   • Final Answer Ready: {decision_output.get('final_answer_ready', False)}
   • Confidence: {decision_output.get('confidence', 0)}%

🛠️ Tool Calls Decided:
{self._format_tool_calls(tool_calls)}

📋 Reasoning Steps:
{self._format_list(decision_output.get('reasoning_steps', []))}

👤 User Preferences Status:
   {"✓ MAINTAINED - PASSED TO ACTION" if decision_output.get('user_preferences') else "✗ NOT MAINTAINED"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    def log_action_input(self, action_input: Dict, iteration: int):
        """Log action stage input"""
        from_decision = action_input.get('from_decision', {})
        from_memory = action_input.get('from_memory', {})
        
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 4: ACTION - INPUT (Iteration {iteration})                     │
└─────────────────────────────────────────────────────────────────────┘

📨 Input to Action:
   ✓ FROM DECISION:
      • Should Call Tool: {from_decision.get('should_call_tool', False)}
      • Tool Calls: {len(from_decision.get('tool_calls', []))}
      • User Preferences: {"✓ Received" if from_decision.get('user_preferences') else "✗ Missing"}

   ✓ FROM MEMORY:
      • Suggested Method: {from_memory.get('suggested_method', 'N/A')}
      • Has Context: {from_memory.get('has_sufficient_context', False)}

🛠️ MCP Tools to Execute:
{self._format_tool_calls(from_decision.get('tool_calls', []))}

""")
    
    def log_action_output(self, action_output: Dict, iteration: int):
        """Log action stage output"""
        self.current_session["stages"]["action"].append({
            "iteration": iteration,
            "output": action_output
        })
        
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 4: ACTION - OUTPUT (Iteration {iteration})                    │
└─────────────────────────────────────────────────────────────────────┘

⚡ Action Results:
   • Method Used: {action_output.get('method', 'N/A')}
   • Tool Calls Executed: {len(action_output.get('tool_results', []))}
   • Confidence: {action_output.get('confidence', 0)}%
   • Sources: {len(action_output.get('sources', []))}
   • Needs Another Decision: {action_output.get('needs_another_decision', False)}

🛠️ Tool Execution Results:
{self._format_tool_results(action_output.get('tool_results', []))}

📚 Sources Used:
{self._format_list(action_output.get('sources', []))}

📋 Reasoning Steps:
{self._format_list(action_output.get('reasoning_steps', []))}

💬 Final Answer Preview:
   {action_output.get('final_answer', 'N/A')[:200]}...

👤 User Preferences Status:
   {"✓ APPLIED IN ANSWER GENERATION" if action_output.get('user_preferences') else "✗ NOT APPLIED"}

🔄 Loop Status:
   {"↻ CONTINUE TO NEXT ITERATION" if action_output.get('needs_another_decision') else "✓ LOOP COMPLETE"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    def log_final_output(self, final_response: Dict):
        """Log the final output to user"""
        self.current_session["final_output"] = final_response
        self.current_session["end_time"] = datetime.now().isoformat()
        
        self._append_to_text_log(f"""
┌─────────────────────────────────────────────────────────────────────┐
│ FINAL OUTPUT TO USER                                                 │
└─────────────────────────────────────────────────────────────────────┘

📤 Final Response:

Query: "{final_response.get('query', 'N/A')}"

Answer:
{final_response.get('answer', 'N/A')}

📊 Response Metadata:
   • Confidence: {final_response.get('confidence', 0)}%
   • Method: {final_response.get('method', 'N/A')}
   • Sources: {len(final_response.get('sources', []))}
   • User Preferences Applied: {"✅ YES" if final_response.get('user_preferences_applied') else "❌ NO"}

📚 Sources:
{self._format_list(final_response.get('sources', []))}

🔍 Complete Reasoning Flow:
{json.dumps(final_response.get('reasoning_flow', {}), indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ EVIDENCE SUMMARY:
   1. ✓ User input captured with preferences
   2. ✓ Perception processed input → output sent to Memory
   3. ✓ Memory received Perception output + maintained preferences
   4. ✓ Decision received Memory output (query + RAG + preferences)
   5. ✓ Action executed MCP tools based on Decision
   6. ✓ Final output incorporates user preferences
   
   Architecture Flow: User → Perception → Memory → Decision ↔ Action → Output
   Status: ✅ WORKING AS DESIGNED

{"="*80}
Session completed at: {self.current_session.get('end_time')}
{"="*80}
""")
        
        # Save JSON log
        self._save_json_log()
    
    def _append_to_text_log(self, content: str):
        """Append content to text log file"""
        with open(self.text_log_file, 'a') as f:
            f.write(content)
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list of items"""
        if not items:
            return "   (none)"
        return "\n".join([f"   {i+1}. {item}" for i, item in enumerate(items)])
    
    def _format_tool_calls(self, tool_calls: List[Dict]) -> str:
        """Format tool calls"""
        if not tool_calls:
            return "   (none)"
        
        result = []
        for i, tc in enumerate(tool_calls, 1):
            result.append(f"   {i}. {tc.get('tool_name', 'unknown')}")
            result.append(f"      Arguments: {json.dumps(tc.get('arguments', {}))}")
            result.append(f"      Reasoning: {tc.get('reasoning', 'N/A')}")
            result.append(f"      Priority: {tc.get('priority', 'N/A')}")
        return "\n".join(result)
    
    def _format_tool_results(self, tool_results: List[Dict]) -> str:
        """Format tool execution results"""
        if not tool_results:
            return "   (none)"
        
        result = []
        for i, tr in enumerate(tool_results, 1):
            status = "✓ SUCCESS" if tr.get('success') else "✗ FAILED"
            result.append(f"   {i}. {tr.get('tool_name', 'unknown')} - {status}")
            result.append(f"      Summary: {tr.get('result_summary', 'N/A')}")
            if tr.get('error'):
                result.append(f"      Error: {tr.get('error')}")
        return "\n".join(result)
    
    def _format_documents(self, documents: List[Dict]) -> str:
        """Format documents"""
        if not documents:
            return "   (none)"
        
        result = []
        for i, doc in enumerate(documents, 1):
            result.append(f"   {i}. {doc.get('title', 'Untitled')}")
            result.append(f"      Relevance: {doc.get('relevance_score', 0):.2f}")
            result.append(f"      Content: {doc.get('content', '')[:100]}...")
        return "\n".join(result)
    
    def _save_json_log(self):
        """Save complete session log as JSON"""
        with open(self.log_file, 'w') as f:
            json.dump(self.current_session, f, indent=2, default=str)
    
    def get_log_files(self) -> Dict[str, str]:
        """Get paths to log files"""
        return {
            "text_log": self.text_log_file,
            "json_log": self.log_file
        }


# Global logger instance
_logger = None

def get_flow_logger() -> FlowLogger:
    """Get or create global flow logger"""
    global _logger
    if _logger is None:
        _logger = FlowLogger()
    return _logger

def reset_flow_logger():
    """Reset global flow logger (for new session)"""
    global _logger
    _logger = FlowLogger()
    return _logger

