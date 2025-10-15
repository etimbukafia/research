import json
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MemoryLayer:
    """
    Tracks conversation history and saves sessions.
    """

    def __init__(self, memory_dir="memory"):
        self.output_dir = Path(__file__).parent.parent / memory_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_session = None
        self.history = []
    
    def start_session(self, query):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.current_session = {
            "query": query,
            "timestamp": timestamp,
            "start_time": datetime.utcnow().isoformat(),
            "steps": []
        }
        self.history = []
        logger.info(f"📝 Started session: {timestamp}")
    
    def add_step(self, step_number, step_data):
        """Recording a reasoning step"""
        if not self.current_session:
            logger.warning("No active session. Call start_session() first.")
            return
        
        record = {
            "step": step_number,
            "timestamp": datetime.utcnow().isoformat(),
            **step_data
        }
        self.history.append(record)
        self.current_session["steps"] = self.history
    
    def save_session(self):
        """Saving session to file"""
        if not self.current_session:
            logger.warning("No session to save")
            return None
        
        timestamp = self.current_session["timestamp"]
        filepath = self.output_dir / f"session_{timestamp}.json"
        
        # Adding summary
        self.current_session["end_time"] = datetime.utcnow().isoformat()
        self.current_session["total_steps"] = len(self.history)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.current_session, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Session saved to {filepath}")
        return str(filepath)
    
    def get_summary(self):
        """Getting summary of current session"""
        if not self.history:
            return "No steps recorded"
        
        total_steps = len(self.history)
        actions_taken = [s.get("action") for s in self.history if s.get("action")]
        
        return {
            "total_steps": total_steps,
            "actions_taken": actions_taken,
            "last_verdict": self.history[-1].get("verification", {}).get("verdict") if self.history else None
        }
    
    def get_context_summary(self, max_steps=3):
        """Getting a summary of recent steps for context"""
        if not self.history:
            return "No previous context"
        
        recent = self.history[-max_steps:]
        summary = []
        
        for step in recent:
            step_num = step.get("step", "?")
            thought = step.get("thought", "")[:100]
            action = step.get("action", "none")
            summary.append(f"Step {step_num}: {thought}... (action: {action})")
        
        return "\n".join(summary)