import logging
from utils.config import DEFAULT_CONFIG
from agents.base_agent import BaseReActAgent

logger = logging.getLogger(__name__)

class AdvancedReactAgent(BaseReActAgent):
    """
    Extended agent that supports verifier and memory plugins.
    Use this when you need quality checking and/or session tracking.
    """
    
    def __init__(self, api_key, tools, config=None, 
                 verifier=None, memory=None, prompt_manager=None):
        super().__init__(api_key, tools, config, prompt_manager)
        self.verifier = verifier
        self.memory = memory
    
    def run(self, query, max_iterations=None, use_verifier=True, use_memory=True):
        """
        Run with optional verifier and memory.
        
        Args:
            query: User question
            max_iterations: Max reasoning loops
            use_verifier: Enable quality checking
            use_memory: Enable session tracking
            
        Returns:
            dict with answer, steps, iterations, success
        """
        max_iter = max_iterations or self.config["max_iterations"]
        steps = []
        
        # Starting memory session
        if use_memory and self.memory:
            self.memory.start_session(query)
        
        # Building initial prompt
        prompt_mode = getattr(self.prompt_manager, "active_mode", "base")
        prompt = self.prompt_manager.compose_prompt(
            query=query,
            tools=self.tools,
            prompt_type=prompt_mode
        )
        
        for iteration in range(1, max_iter + 1):
            logger.info(f"\n{'='*50}\n🔄 Iteration {iteration}\n{'='*50}")
            
            # Calling LLM
            result = self._call_llm(prompt)
            steps.append(result)
            
            thought = result.get("thought", "")
            action = result.get("action", "none")
            action_input = result.get("action_input", "")
            answer = result.get("final_answer", "")
            
            if thought:
                logger.info(f"💭 Thought: {thought[:150]}...")
            if action and action != "none":
                logger.info(f"🔧 Action: {action}")
            
            # Executing tool
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
                        
                        # Converting to string
                        action_input_str = str(action_input).strip()
                        
                        # FALLBACK: If action_input is empty, use the original query
                        if not action_input_str or action_input_str == "":
                            logger.warning(f"⚠️ Empty action_input detected, using original query as fallback")
                            action_input_str = query
                        
                        logger.info(f"📥 Action Input: {action_input_str[:100]}...")
                        observation = tool.execute(action_input_str)
                        logger.info(f"👁 Observation: {observation[:200]}...")
                        
                    except Exception as e:
                        observation = f"Tool error: {e}"
                        logger.error(f"❌ {observation}")
                else:
                    observation = f"Unknown tool: {action}"
                    logger.warning(f"⚠️ {observation}")
                
                prompt += f"\n\nObservation: {observation}\nContinue reasoning."
            
            # Verifying if enabled
            verification = None
            if use_verifier and self.verifier and (thought or answer):
                logger.info("🔍 Running verifier...")
                verification = self.verifier.verify(
                    query=query,
                    agent_answer=answer or thought,
                    observation=observation,
                    context=""  # Can pass domain context here
                )
                
                verdict = verification.get("verdict")
                confidence = verification.get("confidence", 0)
                
                if verdict == "pass":
                    logger.info(f"✅ Verified: PASS (confidence: {confidence})")
                elif verdict == "fail":
                    logger.warning(f"⚠️ Verified: FAIL (confidence: {confidence})")
                    suggestion = verification.get("suggestion", "")
                    logger.info(f"💡 Suggestion: {suggestion}")
                    prompt += f"\n\nVerifier Feedback: {suggestion}\nPlease refine your reasoning."
                else:
                    logger.info(f"❓ Verified: UNCERTAIN")
            
            # Saving to memory
            if use_memory and self.memory:
                self.memory.add_step(iteration, {
                    "thought": thought,
                    "action": action,
                    "action_input": action_input,
                    "observation": observation,
                    "answer": answer,
                    "verification": verification
                })
            
            # Checking if done
            should_stop = (answer and action == "none")
            
            # If verifier is enabled, requiring passing verdict
            if use_verifier and self.verifier and verification:
                should_stop = should_stop and verification.get("verdict") == "pass"
            
            if should_stop:
                logger.info(f"✅ Final Answer: {answer}")
                
                if use_memory and self.memory:
                    session_path = self.memory.save_session()
                    logger.info(f"📄 Session saved to: {session_path}")
                
                return {
                    "answer": answer,
                    "steps": steps,
                    "iterations": iteration,
                    "success": True,
                    "verification": verification
                }
        
        # Max iterations reached
        fallback = answer or "I couldn't find a complete answer."
        logger.warning("⏱️ Max iterations reached")
        
        if use_memory and self.memory:
            self.memory.save_session()
        
        return {
            "answer": fallback,
            "steps": steps,
            "iterations": max_iter,
            "success": False,
            "verification": verification
        }