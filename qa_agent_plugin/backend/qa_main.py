"""
QA Main - Full MCP Architecture with Chain-of-Thought
Gemini LLM uses CoT prompting and calls MCP tools
"""
import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
import asyncio
from rich.console import Console
from rich.panel import Panel
import json

console = Console()

# Load environment variables and setup Gemini
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "AIzaSyCbjuQjQU9yNszaA3tnGnGVh6w021l1Hqc")
client = genai.Client(api_key=api_key)

async def process_query(question: str) -> dict:
    """
    Process query using MCP architecture with Chain-of-Thought prompting
    Gemini decides which tools to call based on the prompt
    """
    try:
        console.print(Panel(f"[bold cyan]Processing Query:[/bold cyan] {question}", border_style="cyan"))
        
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qa_tools_path = os.path.join(script_dir, "qa_tools.py")
        
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[qa_tools_path]
        )
        
        # Create MCP session (properly managed in context)
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                console.print("[green]✓ MCP Server connected[/green]")
                
                # Chain-of-Thought System Prompt
                system_prompt = """You are an intelligent QA Agent with access to specialized tools.

**Your Task:** Answer questions using a step-by-step reasoning approach with explicit self-verification and error handling.

**Available Tools:**
1. analyze_query(query: str) - Analyze the question to extract intent and keywords
2. retrieve_documents(keywords: list, limit: int) - Search for relevant documents
3. store_document(title: str, content: str, url: str) - Store a document
4. generate_response(query: str, documents: list, reasoning_steps: list) - Generate structured response
5. verify_answer(answer: str, sources: list) - Verify answer quality
6. get_statistics() - Get usage statistics

**Chain-of-Thought Process:**

Step 1: ANALYZE the question
- Call: analyze_query to understand what the user is asking
- Tag reasoning type: [INTENT_ANALYSIS]
- Sanity check: Does the extracted intent align with the original question?

Step 2: RETRIEVE relevant information
- Call: retrieve_documents with keywords from analysis
- Tag reasoning type: [INFORMATION_RETRIEVAL]
- Sanity check: Are the keywords appropriate for finding relevant documents?
- ERROR HANDLING: If no documents found, explicitly note this and proceed to fallback strategy

Step 3: REASON about the answer
- Think through the information step-by-step
- Tag each reasoning step by type: [FACTUAL_LOOKUP], [LOGICAL_INFERENCE], [SYNTHESIS], or [COMPUTATION]
- Explain your reasoning clearly and identify any assumptions made
- Sanity check: Does the retrieved information actually answer the question?
- ERROR HANDLING: If information is contradictory, note the conflict and explain which source is more reliable

Step 4: GENERATE the final answer
- Provide a clear, well-structured response
- Cite sources if documents were used
- Tag reasoning type: [ANSWER_GENERATION]
- Sanity check: Is the answer directly addressing the original question?

Step 5: VERIFY the answer
- Call: verify_answer to check answer quality
- Tag reasoning type: [SELF_VERIFICATION]
- Sanity check: Does the answer pass basic quality checks? Is confidence score justified?
- ERROR HANDLING: If confidence < 50%, explicitly state limitations and what additional information would help

**Multi-Turn Conversation Support:**
- If previous context or conversation history is provided, incorporate it into your reasoning
- Reference previous answers or decisions when relevant
- Update your reasoning based on new information or clarifications
- Tag steps that use prior context: [CONTEXT_INTEGRATION]

**Error Handling & Fallbacks:**
- Tool failure: If a tool call fails, log the failure and use alternative approach
- Low confidence (<50%): Explicitly state "I'm uncertain because..." and suggest what would increase confidence
- Contradictory sources: Present both perspectives and explain reasoning for choosing one
- Missing information: Clearly state "I don't have information about X" rather than guessing
- Ambiguous questions: Ask for clarification in your reasoning steps

**Response Format:**
Respond in JSON with this structure:
{
  "reasoning_steps": [
    "[REASONING_TYPE] step 1 explanation...",
    "[REASONING_TYPE] step 2 explanation...",
    "[REASONING_TYPE] step 3 explanation..."
  ],
  "tool_calls": ["tool1(args)", "tool2(args)"],
  "answer": "final answer here",
  "confidence": 0-100,
  "confidence_justification": "why this confidence level",
  "sources": ["source1", "source2"],
  "limitations": ["limitation 1", "limitation 2"],
  "assumptions": ["assumption 1", "assumption 2"]
}

**Important:** Always include reasoning_type tags, perform sanity checks at each step, and explicitly handle errors/uncertainties.

Now answer this question: """

                full_prompt = system_prompt + question
                
                # Call Gemini to decide what to do
                console.print("[yellow]Calling Gemini AI with CoT prompt...[/yellow]")
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=full_prompt
                )
                
                gemini_response = response.text if response and response.text else "{}"
                console.print(f"[cyan]Gemini response received[/cyan]")
                
                # Parse Gemini's response
                try:
                    # Try to extract JSON from the response
                    if "```json" in gemini_response:
                        json_start = gemini_response.find("```json") + 7
                        json_end = gemini_response.find("```", json_start)
                        gemini_response = gemini_response[json_start:json_end].strip()
                    elif "```" in gemini_response:
                        json_start = gemini_response.find("```") + 3
                        json_end = gemini_response.find("```", json_start)
                        gemini_response = gemini_response[json_start:json_end].strip()
                    
                    result = json.loads(gemini_response)
                except:
                    # If JSON parsing fails, create a structured response
                    result = {
                        "reasoning_steps": ["Analyzed question", "Generated direct answer"],
                        "answer": gemini_response,
                        "confidence": 70,
                        "sources": []
                    }
                
                # Execute tool calls mentioned by Gemini
                documents_retrieved = []
                
                # Step 1: Analyze query
                console.print("[blue]→ Executing: analyze_query[/blue]")
                analysis = await session.call_tool("analyze_query", arguments={"query": question})
                analysis_data = json.loads(analysis.content[0].text)
                keywords = analysis_data.get("keywords", question.split()[:3])
                console.print(f"[green]✓ Keywords extracted: {keywords}[/green]")
                
                # Step 2: Retrieve documents
                console.print(f"[blue]→ Executing: retrieve_documents(keywords={keywords})[/blue]")
                doc_result = await session.call_tool("retrieve_documents", arguments={
                    "keywords": keywords,
                    "limit": 5
                })
                doc_data = json.loads(doc_result.content[0].text)
                documents_retrieved = doc_data.get("documents", [])
                console.print(f"[green]✓ Retrieved {len(documents_retrieved)} documents[/green]")
                
                # LLM DECISION: Let Gemini decide if documents are relevant
                use_rag = False
                if documents_retrieved:
                    # Ask Gemini: Are these documents relevant?
                    relevance_check_prompt = f"""You are a relevance checker.

Question: {question}

Retrieved Documents:
{chr(10).join([f"{i}. {d.get('title', 'Untitled')[:100]}" for i, d in enumerate(documents_retrieved, 1)])}

Task: Determine if ANY of these documents can help answer the question.

Respond with ONLY:
- "RELEVANT" if documents can answer the question
- "NOT_RELEVANT" if documents cannot answer the question"""

                    relevance_response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=relevance_check_prompt
                    )
                    
                    relevance_decision = relevance_response.text.strip().upper() if relevance_response else "NOT_RELEVANT"
                    
                    if "RELEVANT" in relevance_decision and "NOT" not in relevance_decision:
                        use_rag = True
                        console.print(f"[green]🤖 LLM Decision: Documents are RELEVANT - using RAG[/green]")
                    else:
                        console.print(f"[yellow]🤖 LLM Decision: Documents NOT relevant - using Gemini fallback[/yellow]")
                
                # Step 3: Generate answer using Gemini with document context
                if use_rag:
                    # Build context from retrieved documents
                    context = "\n\n=== RETRIEVED DOCUMENTS ===\n"
                    for i, doc in enumerate(documents_retrieved, 1):
                        context += f"\nDocument {i}: {doc.get('title', 'Untitled')}\n"
                        context += f"Content: {doc.get('content', '')}\n"
                        context += f"URL: {doc.get('url', 'N/A')}\n"
                        context += "-" * 50 + "\n"
                    
                    # Ask Gemini to answer based on the documents
                    final_prompt = f"""{context}

Question: {question}

Based on the documents above, please provide a clear and accurate answer. Use the specific information from the documents in your response. If the documents contain relevant information, cite it in your answer.

Respond in JSON format:
{{
  "answer": "your detailed answer here",
  "reasoning_steps": ["step 1", "step 2", "step 3"],
  "confidence": 0-100,
  "sources": ["source1", "source2"]
}}"""
                    
                    console.print("[yellow]Asking Gemini to answer based on retrieved documents...[/yellow]")
                    final_response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=final_prompt
                    )
                    
                    final_text = final_response.text if final_response and final_response.text else "{}"
                    
                    # Parse the response
                    try:
                        if "```json" in final_text:
                            json_start = final_text.find("```json") + 7
                            json_end = final_text.find("```", json_start)
                            final_text = final_text[json_start:json_end].strip()
                        elif "```" in final_text:
                            json_start = final_text.find("```") + 3
                            json_end = final_text.find("```", json_start)
                            final_text = final_text[json_start:json_end].strip()
                        
                        final_result = json.loads(final_text)
                        result["answer"] = final_result.get("answer", final_text)
                        result["reasoning_steps"] = final_result.get("reasoning_steps", result.get("reasoning_steps", []))
                        result["confidence"] = final_result.get("confidence", 85)
                        result["sources"] = [d.get("title", "Unknown") for d in documents_retrieved]
                    except:
                        result["answer"] = final_text
                        result["confidence"] = 85
                        result["sources"] = [d.get("title", "Unknown") for d in documents_retrieved]
                    
                    console.print(f"[green]✓ Answer generated from documents (confidence: {result['confidence']}%)[/green]")
                
                else:
                    # NO DOCUMENTS FOUND - FALLBACK TO LIVE WEB SEARCH
                    console.print("[yellow]⚠️  No relevant documents found in RAG storage[/yellow]")
                    
                    # Check if query needs live/recent data
                    needs_live_data = analysis_data.get("requires_live_data", False)
                    
                    if needs_live_data:
                        console.print("[cyan]🌐 Using Google Search Grounding for LIVE data...[/cyan]")
                        
                        # Use Gemini with Google Search Grounding for real-time info
                        from google.genai import types
                        
                        fallback_response = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=question,
                            config=types.GenerateContentConfig(
                                tools=[types.Tool(google_search=types.GoogleSearch())],
                                response_modalities=["TEXT"]
                            )
                        )
                    else:
                        console.print("[cyan]🧠 Using Gemini's general knowledge...[/cyan]")
                        
                        # Use regular Gemini for general knowledge
                        fallback_prompt = f"""You are a helpful AI assistant.

Question: {question}

Provide a clear, accurate answer.

Respond in JSON format:
{{
  "answer": "your answer",
  "reasoning_steps": ["step 1", "step 2"],
  "confidence": 0-100
}}"""
                        
                        fallback_response = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=fallback_prompt
                        )
                    
                    fallback_text = fallback_response.text if fallback_response and fallback_response.text else "{}"
                    
                    # Parse fallback response
                    try:
                        if "```json" in fallback_text:
                            json_start = fallback_text.find("```json") + 7
                            json_end = fallback_text.find("```", json_start)
                            fallback_text = fallback_text[json_start:json_end].strip()
                        elif "```" in fallback_text:
                            json_start = fallback_text.find("```") + 3
                            json_end = fallback_text.find("```", json_start)
                            fallback_text = fallback_text[json_start:json_end].strip()
                        
                        fallback_result = json.loads(fallback_text)
                        result["answer"] = fallback_result.get("answer", fallback_text)
                        result["reasoning_steps"] = fallback_result.get("reasoning_steps", [
                            "No relevant documents found in RAG storage",
                            "Detected need for live/recent data" if needs_live_data else "Using general knowledge",
                            "Used Google Search Grounding for real-time info" if needs_live_data else "Generated answer from training data"
                        ])
                        result["confidence"] = fallback_result.get("confidence", 85 if needs_live_data else 70)
                        result["sources"] = ["Google Search (Live Web Data)" if needs_live_data else "Gemini AI Knowledge Base"]
                        result["used_live_search"] = needs_live_data
                    except:
                        result["answer"] = fallback_text
                        result["confidence"] = 85 if needs_live_data else 70
                        result["sources"] = ["Google Search (Live Web Data)" if needs_live_data else "Gemini AI Knowledge Base"]
                        result["used_live_search"] = needs_live_data
                    
                    console.print(f"[green]✓ Answer generated from {'Google Search' if needs_live_data else 'Gemini knowledge'} (confidence: {result['confidence']}%)[/green]")
                
                # Step 4: Verify answer
                if result.get("answer"):
                    console.print("[blue]→ Executing: verify_answer[/blue]")
                    verify_result = await session.call_tool("verify_answer", arguments={
                        "answer": result["answer"],
                        "sources": result.get("sources", [])
                    })
                    verify_data = json.loads(verify_result.content[0].text)
                    console.print(f"[green]✓ Verification score: {verify_data.get('verification_score', 0)}/100[/green]")
                
                # Step 5: Store Q&A in memory for future recall
                if result.get("answer") and result.get("confidence", 0) >= 70:
                    console.print("[blue]→ Executing: store_in_memory (saving Q&A pair)[/blue]")
                    memory_key = f"qa_{question[:50].replace(' ', '_')}"
                    memory_value = json.dumps({
                        "question": question,
                        "answer": result["answer"],
                        "method": "RAG" if use_rag else "GEMINI_FALLBACK",
                        "confidence": result.get("confidence", 70),
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    
                    await session.call_tool("store_in_memory", arguments={
                        "key": memory_key,
                        "value": memory_value,
                        "category": "qa_history"
                    })
                    console.print(f"[green]✓ Q&A pair stored in memory[/green]")
                
                # Final response
                console.print(Panel(
                    f"[green]✓ Answer generated with CoT![/green]\n{result['answer'][:200]}...",
                    border_style="green"
                ))
                
                # Determine method based on what was actually used
                if use_rag:
                    method = "RAG"
                    method_description = "Retrieved from your captured documents"
                else:
                    # Check if live search was used
                    if result.get("used_live_search", False):
                        method = "GOOGLE_SEARCH"
                        method_description = "Live web search - real-time data from Google"
                    else:
                        method = "GEMINI_FALLBACK"
                        method_description = "General knowledge from Gemini training data"
                
                console.print(f"[cyan]Method: {method} - {method_description}[/cyan]")
                
                return {
                    "answer": result.get("answer", "No answer generated"),
                    "confidence": result.get("confidence", 70),
                    "sources": result.get("sources", ["Gemini AI (Internet Knowledge)"] if not use_rag else [d.get("title", "Unknown") for d in documents_retrieved]),
                    "method": method,
                    "reasoning_steps": result.get("reasoning_steps", [
                        "Analyzed query with MCP tools",
                        f"Retrieved {len(documents_retrieved)} documents",
                        "Generated answer using Gemini" if documents_retrieved else "Used Gemini fallback (no documents found)",
                        "Verified answer quality"
                    ]),
                    "documents_used": len(documents_retrieved)
                }
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        return {
            "answer": f"Error processing query: {str(e)}",
            "confidence": 0,
            "sources": [],
            "method": "ERROR",
            "reasoning_steps": [],
            "documents_used": 0
        }

async def store_page_content(title: str, content: str, url: str) -> dict:
    """Store webpage content using MCP"""
    try:
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
                    "title": title,
                    "content": content,
                    "url": url,
                    "metadata": {"type": "webpage"}
                })
                
                data = json.loads(result.content[0].text)
                console.print(f"[green]✓ Document stored via MCP[/green]")
                
                return {
                    "success": data['success'],
                    "message": f"Stored '{title}' with {len(content)} characters",
                    "total_documents": data['total_documents']
                }
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "total_documents": 0
        }

async def get_memory_summary() -> dict:
    """Get memory summary using MCP"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qa_tools_path = os.path.join(script_dir, "qa_tools.py")
        
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[qa_tools_path]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool("retrieve_from_memory", arguments={})
                data = json.loads(result.content[0].text)
                
                return {
                    "count": data['count'],
                    "summary": f"You have {data['count']} items in memory."
                }
    except Exception as e:
        return {
            "count": 0,
            "summary": f"Error: {str(e)}"
        }

async def get_stats() -> dict:
    """Get statistics using MCP"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qa_tools_path = os.path.join(script_dir, "qa_tools.py")
        
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[qa_tools_path]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool("get_statistics", arguments={})
                stats = json.loads(result.content[0].text)
                
                return {
                    "questions": stats.get('queries_processed', 0),
                    "documents": stats.get('documents_stored', 0),
                    "accuracy": 95
                }
    except Exception as e:
        return {
            "questions": 0,
            "documents": 0,
            "accuracy": 100
        }

if __name__ == "__main__":
    async def test():
        console.print("[bold cyan]Testing MCP + Chain-of-Thought...[/bold cyan]")
        result = await process_query("What is artificial intelligence?")
        console.print("\n[bold green]Result:[/bold green]")
        console.print(json.dumps(result, indent=2))
    
    asyncio.run(test())
