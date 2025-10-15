"""
Gemini AI Agent for Escape Room Challenge
A backend system where an AI agent uses Google's Gemini API to solve puzzles and escape.

Requirements:
    pip install google-generativeai

Usage:
    python escape_room.py
    
Set your API key as environment variable:
    export GEMINI_API_KEY="your-api-key-here"
"""

import google.generativeai as genai
import os
import time
import re
import json
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()


@dataclass
class Puzzle:
    """Represents a single puzzle challenge"""
    id: int
    name: str
    category: str
    description: str
    correct_answer: str
    hints: List[str]
    max_attempts: int
    time_limit_seconds: int
    
    def validate(self, answer: str) -> bool:
        """Check if answer is correct (case-insensitive, whitespace-trimmed)"""
        return answer.strip().lower() == self.correct_answer.strip().lower()


class GameLogger:
    """Handles detailed logging of game events"""
    
    def __init__(self, log_file: str = "escape_room_log.json"):
        self.log_file = log_file
        self.logs = []
        self.session_start = datetime.now()
        
    def log_event(self, event_type: str, data: Dict):
        """Log an event with timestamp"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": (datetime.now() - self.session_start).total_seconds(),
            "event_type": event_type,
            "data": data
        }
        self.logs.append(log_entry)
        
        # Also print to console
        self._print_log(log_entry)
    
    def _print_log(self, entry: Dict):
        """Print log entry to console"""
        timestamp = entry["timestamp"].split("T")[1].split(".")[0]
        event = entry["event_type"]
        data = entry["data"]
        
        print(f"[{timestamp}] {event.upper()}")
        for key, value in data.items():
            print(f"  {key}: {value}")
        print()
    
    def log_game_start(self, total_puzzles: int, time_limit: int):
        """Log game start"""
        self.log_event("GAME_START", {
            "total_puzzles": total_puzzles,
            "time_limit_seconds": time_limit
        })
    
    def log_puzzle_start(self, puzzle: Puzzle):
        """Log when a new puzzle is presented"""
        self.log_event("PUZZLE_START", {
            "puzzle_id": puzzle.id,
            "puzzle_name": puzzle.name,
            "category": puzzle.category,
            "description": puzzle.description[:100] + "..."
        })
    
    def log_agent_reasoning(self, puzzle_id: int, reasoning: str):
        """Log agent's reasoning process"""
        self.log_event("AGENT_REASONING", {
            "puzzle_id": puzzle_id,
            "reasoning": reasoning[:500] + "..." if len(reasoning) > 500 else reasoning
        })
    
    def log_answer_attempt(self, puzzle_id: int, attempt_num: int, answer: str, 
                          is_correct: bool, time_taken: float):
        """Log an answer attempt"""
        self.log_event("ANSWER_ATTEMPT", {
            "puzzle_id": puzzle_id,
            "attempt_number": attempt_num,
            "answer_submitted": answer,
            "is_correct": is_correct,
            "time_taken_seconds": round(time_taken, 2),
            "result": "✅ CORRECT" if is_correct else "❌ INCORRECT"
        })
    
    def log_puzzle_failed(self, puzzle_id: int, reason: str, attempts_made: int):
        """Log puzzle failure"""
        self.log_event("PUZZLE_FAILED", {
            "puzzle_id": puzzle_id,
            "reason": reason,
            "attempts_made": attempts_made
        })
    
    def log_puzzle_solved(self, puzzle_id: int, attempts: int, time_taken: float):
        """Log successful puzzle solve"""
        self.log_event("PUZZLE_SOLVED", {
            "puzzle_id": puzzle_id,
            "attempts_needed": attempts,
            "time_taken_seconds": round(time_taken, 2)
        })
    
    def log_game_end(self, success: bool, puzzles_solved: int, total_time: float, reason: str):
        """Log game end"""
        self.log_event("GAME_END", {
            "success": success,
            "puzzles_solved": puzzles_solved,
            "total_time_seconds": round(total_time, 2),
            "reason": reason
        })
    
    def save_to_file(self):
        """Save logs to JSON file"""
        with open(self.log_file, 'w') as f:
            json.dump({
                "session_start": self.session_start.isoformat(),
                "logs": self.logs
            }, f, indent=2)
        print(f"\n📄 Logs saved to {self.log_file}")


class EscapeRoomEnvironment:
    """Manages the escape room game state and puzzles"""
    
    def __init__(self, total_time_limit: int = 600):
        self.puzzles = self._create_puzzles()
        self.current_puzzle_idx = 0
        self.total_time_limit = total_time_limit
        self.start_time = None
        self.attempts_history = []
        self.hints_used = 0
        self.max_hints = 3
        self.logger = GameLogger()
        
    def _create_puzzles(self) -> List[Puzzle]:
        """Create the sequence of 26 puzzles for the escape room"""
        return [
            # === CIPHER PUZZLES (4 total) ===
            Puzzle(
                id=1,
                name="ROT13 Cipher",
                category="Cipher",
                description="""You find a note with encrypted text: 'URYYB JBEYQ'
                This appears to be a simple substitution cipher. Decode it to proceed.""",
                correct_answer="HELLO WORLD",
                hints=["Try ROT13", "Each letter is shifted by 13 positions"],
                max_attempts=5,
                time_limit_seconds=90
            ),
            Puzzle(
                id=2,
                name="Caesar Cipher",
                category="Cipher",
                description="""A scroll reads: 'DWWDFN DW GDZQ'
                This is encrypted with a Caesar cipher (shift of 3). Decode the message.""",
                correct_answer="ATTACK AT DAWN",
                hints=["Shift each letter back by 3", "A becomes X, B becomes Y, etc."],
                max_attempts=5,
                time_limit_seconds=90
            ),
            Puzzle(
                id=3,
                name="Morse Code",
                category="Cipher",
                description="""You hear tapping sounds forming this pattern:
                '.... . .-.. .--.'
                Decode this morse code message.""",
                correct_answer="HELP",
                hints=["Morse code uses dots and dashes", "H = ...., E = ., L = .-.."],
                max_attempts=5,
                time_limit_seconds=120
            ),
            Puzzle(
                id=4,
                name="Base64 Encoding",
                category="Cipher",
                description="""A computer screen displays: 'U0VDUkVU'
                This is Base64 encoded. Decode it to reveal the password.""",
                correct_answer="SECRET",
                hints=["Base64 is a common encoding scheme", "Try decoding from Base64"],
                max_attempts=5,
                time_limit_seconds=90
            ),
            
            # === SEQUENCE PUZZLES (4 total) ===
            Puzzle(
                id=5,
                name="Doubling Sequence",
                category="Sequence",
                description="""A lock requires a 3-digit code. You find this sequence:
                2, 4, 8, 16, 32, ?
                What is the next number?""",
                correct_answer="64",
                hints=["Look at the pattern", "Each number is doubled"],
                max_attempts=5,
                time_limit_seconds=60
            ),
            Puzzle(
                id=6,
                name="Fibonacci Sequence",
                category="Sequence",
                description="""Numbers are etched on a wall:
                1, 1, 2, 3, 5, 8, 13, ?
                What comes next in this famous sequence?""",
                correct_answer="21",
                hints=["Each number is the sum of the previous two", "This is the Fibonacci sequence"],
                max_attempts=5,
                time_limit_seconds=90
            ),
            Puzzle(
                id=7,
                name="Prime Numbers",
                category="Sequence",
                description="""A digital display shows:
                2, 3, 5, 7, 11, 13, ?
                What is the next number in this sequence?""",
                correct_answer="17",
                hints=["These are prime numbers", "Find the next prime after 13"],
                max_attempts=5,
                time_limit_seconds=90
            ),
            Puzzle(
                id=8,
                name="Square Numbers",
                category="Sequence",
                description="""Tiles are numbered:
                1, 4, 9, 16, 25, ?
                What number should be on the next tile?""",
                correct_answer="36",
                hints=["These are perfect squares", "1², 2², 3², 4², 5², ?"],
                max_attempts=5,
                time_limit_seconds=60
            ),
            
            # === RIDDLE PUZZLES (4 total) ===
            Puzzle(
                id=9,
                name="Echo Riddle",
                category="Riddle",
                description="""A door has this riddle inscribed:
                'I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?'""",
                correct_answer="ECHO",
                hints=["Think about sound", "It repeats what you say"],
                max_attempts=5,
                time_limit_seconds=120
            ),
            Puzzle(
                id=10,
                name="Time Riddle",
                category="Riddle",
                description="""An ancient clock poses a riddle:
                'I have hands but cannot clap. I have a face but cannot see. What am I?'""",
                correct_answer="CLOCK",
                hints=["Think about objects with hands and face", "It tells time"],
                max_attempts=5,
                time_limit_seconds=120
            ),
            Puzzle(
                id=11,
                name="Shadow Riddle",
                category="Riddle",
                description="""A mysterious voice asks:
                'I follow you all day long, but when the night comes I am gone. What am I?'""",
                correct_answer="SHADOW",
                hints=["It appears in light", "It's dark and on the ground"],
                max_attempts=5,
                time_limit_seconds=120
            ),
            Puzzle(
                id=12,
                name="Breath Riddle",
                category="Riddle",
                description="""The final riddle reads:
                'I am always hungry and must be fed. The finger I touch will soon turn red. What am I?'""",
                correct_answer="FIRE",
                hints=["It consumes fuel", "It's hot and dangerous"],
                max_attempts=5,
                time_limit_seconds=120
            ),
            
            # === ANAGRAM PUZZLES (4 total) ===
            Puzzle(
                id=13,
                name="Freedom Anagram",
                category="Anagram",
                description="""Unscramble these letters to find the password:
                'OFREEDM'
                The password is a single word about liberty.""",
                correct_answer="FREEDOM",
                hints=["It's about liberty", "Rearrange all 7 letters"],
                max_attempts=5,
                time_limit_seconds=90
            ),
            Puzzle(
                id=14,
                name="Listen Anagram",
                category="Anagram",
                description="""Rearrange these letters:
                'SILENT'
                Form a word related to hearing.""",
                correct_answer="LISTEN",
                hints=["It's the opposite action", "What you do with your ears"],
                max_attempts=5,
                time_limit_seconds=90
            ),
            Puzzle(
                id=15,
                name="Astronomer Anagram",
                category="Anagram",
                description="""Unscramble this phrase:
                'MOON STARER'
                Two words that form a profession studying space.""",
                correct_answer="ASTRONOMER",
                hints=["Someone who studies stars and planets", "One word, 10 letters"],
                max_attempts=5,
                time_limit_seconds=120
            ),
            Puzzle(
                id=16,
                name="Dormitory Anagram",
                category="Anagram",
                description="""Rearrange these letters:
                'DIRTY ROOM'
                Two words that describe where students sleep.""",
                correct_answer="DORMITORY",
                hints=["Where students live on campus", "One word, 9 letters"],
                max_attempts=5,
                time_limit_seconds=120
            ),
            
            # === MATH PUZZLES (4 total) ===
            Puzzle(
                id=17,
                name="Simple Algebra",
                category="Math",
                description="""Solve for X:
                2X + 5 = 17
                What is X?""",
                correct_answer="6",
                hints=["Subtract 5 from both sides first", "Then divide by 2"],
                max_attempts=5,
                time_limit_seconds=90
            ),
            Puzzle(
                id=18,
                name="Percentage Problem",
                category="Math",
                description="""A safe requires a code:
                What is 25% of 80?""",
                correct_answer="20",
                hints=["25% means 1/4", "Divide 80 by 4"],
                max_attempts=5,
                time_limit_seconds=60
            ),
            Puzzle(
                id=19,
                name="Age Problem",
                category="Math",
                description="""A puzzle states:
                'I am three times as old as you were when I was as old as you are now.
                If I am 40 now, how old are you?'""",
                correct_answer="30",
                hints=["Work backwards from the relationships", "Set up equations for ages"],
                max_attempts=5,
                time_limit_seconds=180
            ),
            Puzzle(
                id=20,
                name="Average Calculation",
                category="Math",
                description="""Find the missing number:
                The average of 5, 10, 15, and X is 12.
                What is X?""",
                correct_answer="18",
                hints=["Average = Sum / Count", "Sum of all numbers = 12 × 4 = 48"],
                max_attempts=5,
                time_limit_seconds=90
            ),
            
            # === LOGIC PUZZLES (4 total) ===
            Puzzle(
                id=21,
                name="Three Switches",
                category="Logic",
                description="""You have 3 switches outside a room. One controls a light bulb inside.
                You can flip switches but only enter the room once. How do you determine which switch controls the bulb?
                Answer with the METHOD: 'HEAT', 'TIME', or 'MULTIPLE'""",
                correct_answer="HEAT",
                hints=["Think about properties other than light", "Light bulbs get hot"],
                max_attempts=5,
                time_limit_seconds=180
            ),
            Puzzle(
                id=22,
                name="Bridge Crossing",
                category="Logic",
                description="""4 people need to cross a bridge at night in 17 minutes max.
                They take 1, 2, 5, and 10 minutes respectively.
                Only 2 can cross at once, and they need the flashlight.
                What is the minimum time needed? (Answer in minutes)""",
                correct_answer="17",
                hints=["The fastest should escort others", "1 and 2 go first, 1 returns"],
                max_attempts=5,
                time_limit_seconds=180
            ),
            Puzzle(
                id=23,
                name="Truth and Lies",
                category="Logic",
                description="""Two doors: one to freedom, one to doom. Two guards: one always tells truth, one always lies.
                You can ask ONE question to ONE guard. What question guarantees escape?
                Answer: 'OTHER' or 'POINT' or 'WOULD'""",
                correct_answer="OTHER",
                hints=["Ask about what the OTHER guard would say", "This cancels out the lie"],
                max_attempts=5,
                time_limit_seconds=180
            ),
            Puzzle(
                id=24,
                name="Water Jugs",
                category="Logic",
                description="""You have a 3-liter jug and a 5-liter jug. How do you measure exactly 4 liters?
                Answer with the final amount in the 5-liter jug after optimal steps.""",
                correct_answer="4",
                hints=["Fill the 5L, pour into 3L", "Empty 3L, transfer remaining from 5L"],
                max_attempts=5,
                time_limit_seconds=180
            ),
            
            # === PATTERN PUZZLES (4 total) ===
            Puzzle(
                id=25,
                name="Letter Pattern",
                category="Pattern",
                description="""Complete the pattern:
                A, C, F, J, O, ?
                What letter comes next?""",
                correct_answer="U",
                hints=["Look at the gaps between letters", "Gaps increase: +1, +2, +3, +4, +5"],
                max_attempts=5,
                time_limit_seconds=120
            ),
            Puzzle(
                id=26,
                name="Number Grid",
                category="Pattern",
                description="""Complete the grid pattern:
                2  4  8
                3  9  27
                4  16 ?
                What number replaces the question mark?""",
                correct_answer="64",
                hints=["Each row follows: N, N², N³", "For row 3: 4, 16, 64"],
                max_attempts=5,
                time_limit_seconds=120
            ),
        ]
    
    def start(self):
        """Start the escape room timer"""
        self.start_time = datetime.now()
        print(f"\n{'='*70}")
        print(f"🔒 ESCAPE ROOM CHALLENGE STARTED 🔒")
        print(f"{'='*70}")
        print(f"Total Time Limit: {self.total_time_limit} seconds ({self.total_time_limit//60} minutes)")
        print(f"Total Puzzles: {len(self.puzzles)}")
        print(f"Hints Available: {self.max_hints}")
        print(f"{'='*70}\n")
        
        self.logger.log_game_start(len(self.puzzles), self.total_time_limit)
    
    def get_current_puzzle(self) -> Optional[Puzzle]:
        """Get the current puzzle"""
        if self.current_puzzle_idx >= len(self.puzzles):
            return None
        return self.puzzles[self.current_puzzle_idx]
    
    def get_time_remaining(self) -> int:
        """Get remaining time in seconds"""
        if not self.start_time:
            return self.total_time_limit
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return max(0, self.total_time_limit - int(elapsed))
    
    def submit_answer(self, answer: str, puzzle_time: float, attempt_num: int) -> Tuple[bool, str]:
        """Submit an answer for the current puzzle"""
        puzzle = self.get_current_puzzle()
        if not puzzle:
            return False, "No more puzzles!"
        
        is_correct = puzzle.validate(answer)
        
        self.attempts_history.append({
            'puzzle_id': puzzle.id,
            'answer': answer,
            'correct': is_correct,
            'time': puzzle_time,
            'attempt_number': attempt_num
        })
        
        # Log the attempt
        self.logger.log_answer_attempt(
            puzzle.id, attempt_num, answer, is_correct, puzzle_time
        )
        
        if is_correct:
            feedback = f"✅ CORRECT! Puzzle {puzzle.id} ({puzzle.name}) solved in {puzzle_time:.1f}s"
            self.logger.log_puzzle_solved(puzzle.id, attempt_num, puzzle_time)
            self.current_puzzle_idx += 1
        else:
            feedback = f"❌ INCORRECT! '{answer}' is not the right answer."
        
        return is_correct, feedback
    
    def get_hint(self) -> Optional[str]:
        """Get a hint for current puzzle"""
        if self.hints_used >= self.max_hints:
            return None
        
        puzzle = self.get_current_puzzle()
        if not puzzle or not puzzle.hints:
            return None
        
        hint_idx = min(self.hints_used, len(puzzle.hints) - 1)
        self.hints_used += 1
        return puzzle.hints[hint_idx]
    
    def is_complete(self) -> bool:
        """Check if all puzzles are solved"""
        return self.current_puzzle_idx >= len(self.puzzles)
    
    def is_time_expired(self) -> bool:
        """Check if time limit exceeded"""
        return self.get_time_remaining() <= 0
    
    def get_summary(self) -> str:
        """Get final game summary"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        solved = self.current_puzzle_idx
        total = len(self.puzzles)
        
        summary = f"\n{'='*70}\n"
        summary += f"🎮 GAME SUMMARY\n"
        summary += f"{'='*70}\n"
        summary += f"Puzzles Solved: {solved}/{total}\n"
        summary += f"Total Time: {total_time:.1f}s ({total_time/60:.1f} minutes)\n"
        summary += f"Hints Used: {self.hints_used}/{self.max_hints}\n"
        summary += f"Total Attempts: {len(self.attempts_history)}\n"
        
        # Calculate success rate
        if self.attempts_history:
            correct = sum(1 for a in self.attempts_history if a['correct'])
            success_rate = (correct / len(self.attempts_history)) * 100
            summary += f"Answer Success Rate: {success_rate:.1f}%\n"
        
        if self.is_complete():
            summary += f"\n🎉 ESCAPED! You solved all {total} puzzles!\n"
            reason = "All puzzles solved successfully"
        elif self.is_time_expired():
            summary += f"\n⏰ TIME EXPIRED! You ran out of time.\n"
            reason = "Time limit exceeded"
        else:
            summary += f"\n💀 FAILED! Could not solve all puzzles.\n"
            reason = "Failed to solve puzzle within attempt limit"
        
        summary += f"{'='*70}\n"
        
        # Log game end
        self.logger.log_game_end(
            success=self.is_complete(),
            puzzles_solved=solved,
            total_time=total_time,
            reason=reason
        )
        
        return summary


class GeminiAgent:
    """AI Agent that uses Gemini to solve escape room puzzles"""
    
    def __init__(self, api_key: str, logger: GameLogger, model_name: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.conversation_history = []
        self.solved_answers = []  # Track all correct answers
        self.logger = logger
        
    def solve_puzzle(self, puzzle: Puzzle, time_remaining: int) -> str:
        """Use Gemini to solve a puzzle"""
        print(f"\n{'─'*70}")
        print(f"🧩 PUZZLE {puzzle.id}: {puzzle.name} ({puzzle.category})")
        print(f"{'─'*70}")
        print(f"Description: {puzzle.description}")
        print(f"Time Remaining: {time_remaining}s ({time_remaining//60}m {time_remaining%60}s)")
        print(f"Max Attempts: {puzzle.max_attempts}")
        print(f"{'─'*70}\n")
        
        # Log puzzle start
        self.logger.log_puzzle_start(puzzle)
        
        # Build context from previous answers for multi-step puzzles
        context = ""
        if self.solved_answers:
            context = f"\nPrevious puzzle answers you've solved:\n"
            for i, ans in enumerate(self.solved_answers, 1):
                context += f"  Puzzle {i}: {ans}\n"
        
        prompt = f"""You are an AI agent trying to escape from a room by solving puzzles.

{context}
Current Puzzle ({puzzle.category}):
{puzzle.description}

Instructions:
1. Think through the puzzle carefully and methodically
2. Show your reasoning process step by step
3. Provide your final answer on a new line starting with "ANSWER:"
4. Your answer should be concise - just the solution (a word, number, or phrase)

Your response format should be:
Reasoning: [your step-by-step thinking]
ANSWER: [your final answer only]

Solve this puzzle now."""

        print("🤖 Agent thinking...")
        
        try:
            response = self.model.generate_content(prompt)
            full_response = response.text
            
            print(f"\n💭 Agent's Reasoning:")
            print(f"{'─'*70}")
            print(full_response)
            print(f"{'─'*70}\n")
            
            # Log agent reasoning
            self.logger.log_agent_reasoning(puzzle.id, full_response)
            
            # Extract answer
            answer = self._extract_answer(full_response)
            print(f"📝 Agent's Answer: '{answer}'")
            
            return answer
            
        except Exception as e:
            error_msg = f"⚠️  Error calling Gemini API: {e}"
            print(error_msg)
            self.logger.log_event("API_ERROR", {
                "puzzle_id": puzzle.id,
                "error": str(e)
            })
            return ""
    
    def _extract_answer(self, response: str) -> str:
        """Extract the answer from Gemini's response"""
        # Look for "ANSWER:" pattern
        match = re.search(r'ANSWER:\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if match:
            answer = match.group(1).strip()
        else:
            # Fallback: try to get last line
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            answer = lines[-1] if lines else response.strip()
        
        # Clean up common article prefixes
        answer = re.sub(r'^(an?|the)\s+', '', answer, flags=re.IGNORECASE)
        
        # Remove common punctuation at the end
        answer = answer.rstrip('.,;:!?')
        
        return answer.strip()
    
    def record_success(self, answer: str):
        """Record a successfully solved answer"""
        self.solved_answers.append(answer)


def main():
    """Main game loop"""
    # Get API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        print("Set it with: export GEMINI_API_KEY='your-key-here'")
        return
    
    # Initialize environment and agent
    environment = EscapeRoomEnvironment(total_time_limit=1200)  # 20 minutes for 26 puzzles
    agent = GeminiAgent(api_key, environment.logger)
    
    # Start the game
    environment.start()
    
    # Main game loop
    while not environment.is_complete() and not environment.is_time_expired():
        puzzle = environment.get_current_puzzle()
        if not puzzle:
            break
        
        time_remaining = environment.get_time_remaining()
        puzzle_start_time = time.time()
        
        # Agent attempts to solve
        attempt_count = 0
        solved = False
        
        while attempt_count < puzzle.max_attempts and not solved and not environment.is_time_expired():
            attempt_count += 1
            print(f"\n🎯 Attempt {attempt_count}/{puzzle.max_attempts}")
            
            answer = agent.solve_puzzle(puzzle, time_remaining)
            puzzle_time = time.time() - puzzle_start_time
            
            is_correct, feedback = environment.submit_answer(answer, puzzle_time, attempt_count)
            print(f"\n{feedback}\n")
            
            if is_correct:
                agent.record_success(answer)
                solved = True
                time.sleep(1)  # Brief pause between puzzles
            else:
                # Check if we should continue
                if attempt_count >= puzzle.max_attempts:
                    print(f"❌ Max attempts ({puzzle.max_attempts}) reached for puzzle {puzzle.id}")
                    environment.logger.log_puzzle_failed(
                        puzzle.id,
                        "Max attempts exceeded",
                        attempt_count
                    )
                    break
                
                if environment.is_time_expired():
                    print(f"⏰ Time expired during puzzle {puzzle.id}")
                    environment.logger.log_puzzle_failed(
                        puzzle.id,
                        "Time expired",
                        attempt_count
                    )
                    break
                    
                print("🔄 Trying again...\n")
                time.sleep(0.5)
        
        if not solved:
            if environment.is_time_expired():
                print(f"\n⏰ GAME OVER: Time limit reached at puzzle {puzzle.id}")
            else:
                print(f"\n💀 Failed to solve puzzle {puzzle.id} - Game Over")
            break
    
    # Game over
    print(environment.get_summary())
    
    # Save logs
    environment.logger.save_to_file()
    print(f"\n📊 Detailed logs available in: escape_room_log.json")


if __name__ == "__main__":
    main()