import requests
import json
import re
import logging
import time

logger = logging.getLogger(__name__)

class VerifierAgent:
    """
    Verifies the quality of agent's reasoning and answers.
    """
    
    def __init__(self, api_key, model="z-ai/glm-4.5-air:free"):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def verify(self, query, agent_answer, observation, context=""):
        """Checking if the agent's reasoning makes sense."""
        is_final_answer = not observation or observation.strip() == ""
        
        prompt = f"""You are an answer quality verifier for AI researches from an assistant. Evaluate the reasoning step.

Original Question: {query}

Agent's Thought/Answer: {agent_answer}

Tool Observation: {observation if observation else "(No tool was used - this is a final synthesis step)"}

Context: {context or "No additional context"}

Evaluation Criteria:
1. Is the reasoning logical and coherent?
2. Does it address the original question?
{"3. Is this a reasonable final answer based on previous context?" if is_final_answer else "3. Is the tool usage appropriate for gathering information?"}
4. Are there any logical errors or unsupported claims?

{"Note: This appears to be a final answer step (no tool usage), so focus on answer quality rather than tool selection." if is_final_answer else ""}

Respond in JSON:
{{
  "verdict": "pass" or "fail",
  "reason": "brief explanation of your verdict",
  "suggestion": "how to improve (if fail, otherwise empty string)",
  "confidence": 0.0 to 1.0
}}"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }

        try:
            logger.info("🔍 [Verifier] Starting verification step...")
            logger.debug(f"[Verifier] Payload:\n{json.dumps(data, indent=2)[:1000]}")

            start_time = time.time()
            response = requests.post(self.url, json=data, headers=headers, timeout=45)
            elapsed = time.time() - start_time
            logger.info(f"⏱️ [Verifier] Response received in {elapsed:.2f}s")

            response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"].strip()
            logger.debug(f"🧾 [Verifier] Raw LLM Output:\n{content[:800]}")

            # Extract JSON
            json_match = re.search(r'\{[\s\S]*?\}', content)
            if json_match:
                result = json.loads(json_match.group(0))
                logger.info(f"✅ [Verifier] Verdict: {result.get('verdict')} | Confidence: {result.get('confidence')}")
                return result

            logger.warning("⚠️ [Verifier] Could not parse model response as JSON.")
            return {
                "verdict": "uncertain",
                "reason": "Could not parse verifier response",
                "suggestion": "",
                "confidence": 0.0
            }

        except requests.Timeout:
            logger.error("⏰ [Verifier] Request timed out.")
            return {
                "verdict": "uncertain",
                "reason": "Verifier request timed out",
                "suggestion": "",
                "confidence": 0.0
            }

        except Exception as e:
            logger.error(f"❌ [Verifier] Internal error: {e}")
            return {
                "verdict": "uncertain",
                "reason": f"Verifier error: {str(e)}",
                "suggestion": "",
                "confidence": 0.0
            }
