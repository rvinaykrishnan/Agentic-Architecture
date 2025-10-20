"""
Perception Module - Understands user input and intent
Includes system prompt evaluation and LLM-based query analysis
"""
import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from google import genai
from rich.console import Console
import json

console = Console()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UserPreference(BaseModel):
    """User preferences that personalize the agent's behavior"""
    preferred_language: str = Field(default="English", description="User's preferred language for responses")
    expertise_level: str = Field(default="intermediate", description="User's expertise level: beginner, intermediate, expert")
    response_style: str = Field(default="balanced", description="Response style: concise, balanced, detailed")
    focus_areas: List[str] = Field(default_factory=list, description="User's areas of interest or expertise")
    location: Optional[str] = Field(default=None, description="User's location for context-aware responses")
    preferred_sources: List[str] = Field(default_factory=list, description="Preferred types of sources: academic, news, blogs, official docs")
    time_sensitivity: str = Field(default="moderate", description="How important timeliness is: low, moderate, high")
    depth_preference: str = Field(default="moderate", description="Depth of explanation: shallow, moderate, deep")
    
    class Config:
        json_schema_extra = {
            "example": {
                "preferred_language": "English",
                "expertise_level": "intermediate",
                "response_style": "balanced",
                "focus_areas": ["technology", "science", "AI"],
                "location": "San Francisco, USA",
                "preferred_sources": ["academic", "official docs"],
                "time_sensitivity": "high",
                "depth_preference": "deep"
            }
        }


class QueryInput(BaseModel):
    """Input for query understanding"""
    query: str = Field(..., description="User's question or query")
    conversation_history: List[Dict] = Field(default_factory=list, description="Previous conversation context")


class PerceptionOutput(BaseModel):
    """Output from perception analysis"""
    original_query: str
    analyzed_intent: str = Field(..., description="The understood intent of the query")
    query_type: str = Field(..., description="Type of query: FACTUAL, COMPARATIVE, TEMPORAL, PROCEDURAL, OPINION")
    requires_live_data: bool = Field(..., description="Whether query needs real-time/current information")
    requires_deep_reasoning: bool = Field(..., description="Whether query needs multi-step reasoning")
    extracted_keywords: List[str] = Field(..., description="Key terms for retrieval")
    reasoning_steps: List[str] = Field(..., description="Step-by-step analysis of the query")
    confidence: float = Field(..., ge=0, le=100, description="Confidence in understanding (0-100)")
    user_preferences: Optional[UserPreference] = Field(None, description="User preferences for personalization")
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "What is quantum computing?",
                "analyzed_intent": "User wants to understand the concept of quantum computing",
                "query_type": "FACTUAL",
                "requires_live_data": False,
                "requires_deep_reasoning": False,
                "extracted_keywords": ["quantum", "computing"],
                "reasoning_steps": ["Identified factual question", "Extracted key concepts"],
                "confidence": 95.0,
                "user_preferences": None
            }
        }


# ============================================================================
# PERCEPTION AGENT CLASS
# ============================================================================

class PerceptionAgent:
    """
    Perception Agent - First stage of the agentic architecture
    Responsible for understanding user input with Chain-of-Thought reasoning
    """
    
    def __init__(self, api_key: str, user_preferences: Optional[UserPreference] = None):
        """Initialize perception agent with API key and optional user preferences"""
        self.client = genai.Client(api_key=api_key)
        self.user_preferences = user_preferences
        self.system_prompt = self._build_system_prompt()
        
    def _build_system_prompt(self) -> str:
        """
        Build system prompt that fulfills all validation criteria:
        ✅ Explicit Reasoning Instructions
        ✅ Structured Output Format (JSON)
        ✅ Separation of Reasoning and Tools
        ✅ Conversation Loop Support
        ✅ Instructional Framing (with examples)
        ✅ Internal Self-Checks
        ✅ Reasoning Type Awareness
        ✅ Error Handling/Fallbacks
        ✅ Overall Clarity and Robustness
        """
        
        preference_context = ""
        if self.user_preferences:
            preference_context = f"""
**USER PREFERENCES (CRITICAL - Must incorporate in all analysis):**
- Language: {self.user_preferences.preferred_language}
- Expertise Level: {self.user_preferences.expertise_level}
- Response Style: {self.user_preferences.response_style}
- Focus Areas: {', '.join(self.user_preferences.focus_areas) if self.user_preferences.focus_areas else 'General'}
- Location Context: {self.user_preferences.location or 'Not specified'}
- Preferred Sources: {', '.join(self.user_preferences.preferred_sources) if self.user_preferences.preferred_sources else 'Any reliable source'}
- Time Sensitivity: {self.user_preferences.time_sensitivity}
- Depth Preference: {self.user_preferences.depth_preference}

**IMPORTANT:** Always tailor your analysis and understanding based on these preferences.
"""
        
        return f"""You are the PERCEPTION module of an intelligent QA Agent system.

{preference_context}

**YOUR ROLE:** Analyze and understand user queries with explicit step-by-step reasoning.

**CRITICAL INSTRUCTIONS - THINK BEFORE YOU RESPOND:**

1. **EXPLICIT REASONING (MANDATORY):**
   - Think through EVERY step before drawing conclusions
   - Tag each reasoning step with its type in square brackets
   - Explain your thinking process clearly
   - Question your own assumptions at each step

2. **REASONING TYPE TAGS (Use these explicitly):**
   - [INTENT_ANALYSIS] - Understanding what user wants
   - [ENTITY_EXTRACTION] - Identifying key concepts/entities
   - [TEMPORAL_CHECK] - Checking if current/recent data needed
   - [COMPLEXITY_ASSESSMENT] - Evaluating reasoning depth required
   - [CONTEXT_INTEGRATION] - Incorporating conversation history
   - [SELF_VERIFICATION] - Sanity checking your analysis
   - [PREFERENCE_ALIGNMENT] - Ensuring user preferences are considered

3. **STEP-BY-STEP PROCESS (Follow strictly):**

   Step 1: [INTENT_ANALYSIS] Understand the core intent
   - What is the user truly asking?
   - Is it factual, comparative, procedural, or opinion-based?
   - SANITY CHECK: Does my interpretation align with the actual words used?

   Step 2: [ENTITY_EXTRACTION] Extract key concepts
   - What are the main subjects/entities?
   - What are the important keywords for retrieval?
   - SANITY CHECK: Are these keywords sufficient and relevant?

   Step 3: [TEMPORAL_CHECK] Assess time sensitivity
   - Does this require current/live data? (e.g., "latest", "today", "current")
   - Or is it asking about established knowledge?
   - SANITY CHECK: Am I certain about the temporal requirement?

   Step 4: [COMPLEXITY_ASSESSMENT] Evaluate reasoning needs
   - Is this a simple factual lookup?
   - Or does it need multi-step reasoning/comparison?
   - SANITY CHECK: Have I correctly assessed the complexity?

   Step 5: [CONTEXT_INTEGRATION] Check conversation history
   - Are there previous questions that provide context?
   - Does "this", "that", "it" refer to something earlier?
   - SANITY CHECK: Am I using context appropriately?

   Step 6: [PREFERENCE_ALIGNMENT] Apply user preferences
   - How should preferences influence understanding?
   - Does expertise level affect how I interpret the query?
   - SANITY CHECK: Have I incorporated ALL relevant preferences?

   Step 7: [SELF_VERIFICATION] Verify your analysis
   - Review all previous steps for consistency
   - Identify any gaps or uncertainties
   - Assign confidence score based on clarity and completeness

4. **STRUCTURED OUTPUT FORMAT (MANDATORY JSON):**
   ```json
   {{
     "original_query": "exact user query",
     "analyzed_intent": "clear description of what user wants",
     "query_type": "FACTUAL|COMPARATIVE|TEMPORAL|PROCEDURAL|OPINION",
     "requires_live_data": true/false,
     "requires_deep_reasoning": true/false,
     "extracted_keywords": ["keyword1", "keyword2", "keyword3"],
     "reasoning_steps": [
       "[REASONING_TYPE] explanation of step 1",
       "[REASONING_TYPE] explanation of step 2",
       "[REASONING_TYPE] explanation of step 3"
     ],
     "confidence": 85,
     "uncertainties": ["uncertainty 1 if any"],
     "assumptions": ["assumption 1 if any"]
   }}
   ```

5. **ERROR HANDLING & FALLBACKS:**
   - Ambiguous query: State "Query is ambiguous because..." and make best interpretation
   - Missing context: Note "Missing context: ..." and proceed with assumptions
   - Conflicting signals: Explain conflict and choose most likely interpretation
   - Low confidence (<60%): Explicitly list what would increase confidence
   - Unknown terms: Flag them but continue with available information

6. **CONVERSATION LOOP SUPPORT:**
   - Always check for conversation_history in input
   - Reference previous queries/answers when relevant
   - Update understanding based on new information
   - Maintain consistency with previous interactions

7. **EXAMPLES OF GOOD ANALYSIS:**

   Example 1:
   Query: "What's the latest on AI regulations?"
   Reasoning:
   - [INTENT_ANALYSIS] User wants current information about AI regulations
   - [ENTITY_EXTRACTION] Keywords: AI, regulations, latest, current policy
   - [TEMPORAL_CHECK] "latest" indicates need for real-time data
   - [COMPLEXITY_ASSESSMENT] Moderate - needs recent sources but straightforward
   - [SELF_VERIFICATION] Confident this needs live/recent data ✓
   Result: {{query_type: "TEMPORAL", requires_live_data: true, confidence: 95}}

   Example 2:
   Query: "How does photosynthesis work?"
   Reasoning:
   - [INTENT_ANALYSIS] User wants to understand a biological process
   - [ENTITY_EXTRACTION] Keywords: photosynthesis, process, mechanism
   - [TEMPORAL_CHECK] Established scientific knowledge, no live data needed
   - [COMPLEXITY_ASSESSMENT] May need step-by-step explanation
   - [PREFERENCE_ALIGNMENT] User expertise level {self.user_preferences.expertise_level if self.user_preferences else 'intermediate'} - adjust depth accordingly
   - [SELF_VERIFICATION] Clear factual question about established science ✓
   Result: {{query_type: "FACTUAL", requires_live_data: false, requires_deep_reasoning: true, confidence: 98}}

**CRITICAL REMINDERS:**
- ALWAYS include reasoning_type tags in your reasoning_steps
- ALWAYS perform self-verification at each major step
- ALWAYS consider user preferences when provided
- ALWAYS handle uncertainties explicitly
- NEVER skip steps or rush to conclusions
- NEVER output anything except valid JSON

Now analyze the following query with explicit reasoning:"""

    def understand_query(self, query_input: QueryInput) -> PerceptionOutput:
        """
        Understand and analyze the user's query with Chain-of-Thought reasoning
        
        Args:
            query_input: QueryInput containing query and conversation history
            
        Returns:
            PerceptionOutput with detailed analysis
        """
        try:
            console.print("[bold cyan]🧠 PERCEPTION: Analyzing query...[/bold cyan]")
            
            # Prepare the prompt with conversation context
            context = ""
            if query_input.conversation_history:
                context = "\n\n**CONVERSATION HISTORY:**\n"
                for i, msg in enumerate(query_input.conversation_history[-3:], 1):  # Last 3 messages
                    context += f"{i}. Q: {msg.get('query', '')} → A: {msg.get('answer', '')[:100]}...\n"
            
            full_prompt = f"{self.system_prompt}\n{context}\n\n**QUERY TO ANALYZE:** {query_input.query}"
            
            # Call Gemini for analysis
            console.print("[yellow]→ Calling Gemini for query understanding...[/yellow]")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=full_prompt
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
                
                analysis = json.loads(response_text)
                
                # CRITICAL FIX: Ensure temporal keywords are detected
                # Override requires_live_data if temporal keywords are found
                temporal_keywords = ['latest', 'recent', 'today', 'yesterday', 'now', 'current', 'breaking', 'just', 'this week', 'this month']
                query_lower = query_input.query.lower()
                if any(keyword in query_lower for keyword in temporal_keywords):
                    analysis['requires_live_data'] = True
                    console.print(f"[yellow]⚠️  Temporal keyword detected - forcing requires_live_data=True[/yellow]")
                
                # Create PerceptionOutput with user preferences
                output = PerceptionOutput(
                    original_query=query_input.query,
                    analyzed_intent=analysis.get("analyzed_intent", "Unknown intent"),
                    query_type=analysis.get("query_type", "FACTUAL"),
                    requires_live_data=analysis.get("requires_live_data", False),
                    requires_deep_reasoning=analysis.get("requires_deep_reasoning", False),
                    extracted_keywords=analysis.get("extracted_keywords", query_input.query.split()[:5]),
                    reasoning_steps=analysis.get("reasoning_steps", []),
                    confidence=analysis.get("confidence", 70.0),
                    user_preferences=self.user_preferences
                )
                
                console.print(f"[green]✓ Query understood with {output.confidence}% confidence[/green]")
                console.print(f"[cyan]  Intent: {output.analyzed_intent}[/cyan]")
                console.print(f"[cyan]  Type: {output.query_type}[/cyan]")
                console.print(f"[cyan]  Keywords: {', '.join(output.extracted_keywords)}[/cyan]")
                
                return output
                
            except json.JSONDecodeError as e:
                console.print(f"[yellow]⚠️  JSON parsing failed, using fallback analysis[/yellow]")
                
                # Fallback: Basic analysis
                return PerceptionOutput(
                    original_query=query_input.query,
                    analyzed_intent=f"Understand: {query_input.query}",
                    query_type="FACTUAL",
                    requires_live_data=any(word in query_input.query.lower() for word in ['latest', 'recent', 'today', 'now', 'current']),
                    requires_deep_reasoning=len(query_input.query.split()) > 10,
                    extracted_keywords=[w for w in query_input.query.lower().split() if len(w) > 3][:5],
                    reasoning_steps=[
                        "[FALLBACK] Using basic keyword extraction",
                        "[FALLBACK] Performing simple temporal check",
                        "[FALLBACK] Analysis completed with reduced confidence"
                    ],
                    confidence=60.0,
                    user_preferences=self.user_preferences
                )
                
        except Exception as e:
            console.print(f"[red]❌ Error in perception: {e}[/red]")
            import traceback
            traceback.print_exc()
            
            # Emergency fallback
            return PerceptionOutput(
                original_query=query_input.query,
                analyzed_intent="Error in analysis",
                query_type="FACTUAL",
                requires_live_data=False,
                requires_deep_reasoning=False,
                extracted_keywords=[query_input.query.split()[0]] if query_input.query.split() else ["unknown"],
                reasoning_steps=[f"[ERROR] {str(e)}"],
                confidence=0.0,
                user_preferences=self.user_preferences
            )


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    # Test with user preferences
    preferences = UserPreference(
        preferred_language="English",
        expertise_level="intermediate",
        response_style="detailed",
        focus_areas=["technology", "AI", "science"],
        location="San Francisco, USA",
        preferred_sources=["academic", "official docs"],
        time_sensitivity="high",
        depth_preference="deep"
    )
    
    agent = PerceptionAgent(api_key=api_key, user_preferences=preferences)
    
    # Test queries
    test_queries = [
        "What is artificial intelligence?",
        "What's the latest news on climate change?",
        "How does blockchain compare to traditional databases?"
    ]
    
    for query in test_queries:
        console.print(f"\n[bold magenta]{'='*60}[/bold magenta]")
        query_input = QueryInput(query=query)
        result = agent.understand_query(query_input)
        console.print(f"\n[bold green]Result:[/bold green]\n{result.model_dump_json(indent=2)}")

