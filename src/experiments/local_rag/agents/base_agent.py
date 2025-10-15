import requests
import json
import re
import logging
import os
from pathlib import Path

from utils.prompt_manager import PromptManager
from utils.config import DEFAULT_CONFIG


logger = logging.getLogger(__name__)



class BaseReActAgent:
    """
    Simple ReAct agent - no plugins, no complexity.
    Just the basic reasoning loop.
    """
    
    def __init__(self, api_key, tools, config=None, prompt_manager=None):
        self.api_key = api_key
        self.tools = {tool.name: tool for tool in tools}
        self.config = config or DEFAULT_CONFIG.copy()
        self.prompt_manager = prompt_manager or PromptManager()
        
        # Setting up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _call_llm(self, prompt):
        """Calling the LLM through OpenRouter and safely parsing JSON output (single or multi-block)."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.get("temperature", 0.3),
        }

        try:
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=self.config.get("timeout", 45)
            )
            response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"].strip()
            logger.debug(f"🧾 Raw LLM output:\n{content[:800]}")

            # Cleaning common artifacts (</think>, etc.)
            content = content.replace("</think>", "")

            # Finding all JSON-like blocks (handles multiple reasoning outputs)
            json_blocks = re.findall(r'\{[\s\S]*?\}', content)
            parsed_blocks = []

            for block in json_blocks:
                try:
                    parsed = json.loads(block)
                    
                    # CRITICAL: Removing any LLM-hallucinated observation
                    # The observation field should ONLY contain actual tool output
                    if "observation" in parsed:
                        logger.warning("⚠️ LLM included 'observation' field - removing (observation comes from tool execution only)")
                        parsed["observation"] = ""
                    
                    parsed_blocks.append(parsed)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping malformed JSON block: {e}")

            if parsed_blocks:
                if len(parsed_blocks) > 1:
                    logger.info(f"Parsed {len(parsed_blocks)} reasoning blocks — using last as final.")
                return parsed_blocks[-1]  # returning last reasoning step

            # Fallback: no JSON at all
            logger.warning(f"⚠️ Model returned non-JSON output:\n{content[:400]}")
            return {
                "thought": "",
                "action": "none",
                "action_input": "",
                "observation": "",
                "final_answer": content or "No output from model"
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}\nRaw content:\n{content[:400]}")
            return {
                "thought": "",
                "action": "none",
                "action_input": "",
                "observation": f"JSON error: {e}",
                "final_answer": content
            }

        except Exception as e:
            logger.error(f"❌ LLM call failed: {e}")
            return {
                "thought": "",
                "action": "none",
                "action_input": "",
                "observation": f"Error: {e}",
                "final_answer": ""
            } 
    
    def _format_tools(self):
        """Formatting tool descriptions for prompt"""
        tool_list = []
        for tool in self.tools.values():
            tool_list.append(f"- {tool.name}: {tool.description}")
        return "\n".join(tool_list)
    
    def run(self, query, max_iterations=None):
        """
        Running the agent on a query.
        Returns: dict with 'answer' and 'steps'
        """
        max_iter = max_iterations or self.config["max_iterations"]
        steps = []
        
        # Building initial prompt
        tools_str = self._format_tools()
        prompt = self.prompt_manager.get_prompt(
            "base",
            tools=tools_str,
            query=query
        )
        
        for iteration in range(1, max_iter + 1):
            logger.info(f"\n{'='*50}\nIteration {iteration}\n{'='*50}")
            
            # Calling LLM
            result = self._call_llm(prompt)
            
            thought = result.get("thought", "")
            action = result.get("action", "none")
            action_input = result.get("action_input", "")
            answer = result.get("final_answer", "")
            
            # Logging what's happening
            if thought:
                logger.info(f"💭 Thought: {thought[:150]}...")
            if action and action != "none":
                logger.info(f"🔧 Action: {action}")
                logger.info(f"📥 Input: {action_input}")
            
            # Executing tool if needed
            observation = ""
            if action and action != "none":
                tool = self.tools.get(action)
                if tool:
                    try:
                        # Normalizing input
                        if isinstance(action_input, list):
                            action_input = " ".join(map(str, action_input))
                        elif isinstance(action_input, dict):
                            action_input = " ".join(f"{k}: {v}" for k, v in action_input.items())
                        
                        action_input_str = str(action_input).strip()
                        
                        # FALLBACK: If action_input is empty, using original query
                        if not action_input_str:
                            logger.warning(f"⚠️ Empty action_input detected, using original query as fallback")
                            action_input_str = query
                        
                        observation = tool.execute(action_input_str)
                        logger.info(f"👁 Observation (first 200 chars): {observation[:200]}...")
                        
                    except Exception as e:
                        observation = f"Tool error: {e}"
                        logger.error(f"❌ {observation}")
                else:
                    observation = f"Unknown tool: {action}"
                    logger.warning(f"⚠️ {observation}")
                
                # Updating result with ACTUAL observation from tool
                result["observation"] = observation
                
                # Adding observation to prompt for next iteration
                prompt += f"\n\nObservation: {observation}\nContinue reasoning and respond in JSON format."
            
            # Adding complete step (with real observation) to history
            steps.append(result)
            
            # Checking if we have final answer
            if answer and action == "none":
                logger.info(f"✅ Final Answer: {answer}")
                return {
                    "answer": answer,
                    "steps": steps,
                    "iterations": iteration,
                    "success": True
                }
        
        # Max iterations reached
        fallback = answer or "I couldn't find a complete answer."
        logger.warning("⏱️ Max iterations reached")
        return {
            "answer": fallback,
            "steps": steps,
            "iterations": max_iter,
            "success": False
        }