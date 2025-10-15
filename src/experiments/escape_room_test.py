"""
Test Suite for Gemini AI Escape Room Agent
Comprehensive tests to ensure the escape room environment works correctly.

Requirements:
    pip install google-generativeai pytest

Usage:
    pytest test_escape_room.py -v
    or
    python test_escape_room.py
"""

import unittest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys


# Import the classes from the main escape room module
# Assuming the main file is named 'escape_room.py'
try:
    from escape_room import EscapeRoomEnvironment, GeminiAgent, Puzzle
except ImportError:
    print("Warning: Could not import from escape_room.py")
    print("Make sure escape_room.py is in the same directory")
    # Define minimal versions for testing if import fails
    from dataclasses import dataclass
    from typing import List, Optional, Tuple
    
    @dataclass
    class Puzzle:
        id: int
        name: str
        description: str
        correct_answer: str
        hints: List[str]
        max_attempts: int
        time_limit_seconds: int
        
        def validate(self, answer: str) -> bool:
            return answer.strip().lower() == self.correct_answer.strip().lower()


class TestPuzzle(unittest.TestCase):
    """Test the Puzzle class"""
    
    def setUp(self):
        self.puzzle = Puzzle(
            id=1,
            name="Test Puzzle",
            description="A test puzzle",
            correct_answer="TEST",
            hints=["Hint 1", "Hint 2"],
            max_attempts=3,
            time_limit_seconds=60
        )
    
    def test_puzzle_creation(self):
        """Test puzzle object creation"""
        self.assertEqual(self.puzzle.id, 1)
        self.assertEqual(self.puzzle.name, "Test Puzzle")
        self.assertEqual(self.puzzle.correct_answer, "TEST")
        self.assertEqual(len(self.puzzle.hints), 2)
    
    def test_puzzle_validation_correct(self):
        """Test correct answer validation"""
        self.assertTrue(self.puzzle.validate("TEST"))
        self.assertTrue(self.puzzle.validate("test"))  # Case insensitive
        self.assertTrue(self.puzzle.validate("  TEST  "))  # Whitespace trimmed
    
    def test_puzzle_validation_incorrect(self):
        """Test incorrect answer validation"""
        self.assertFalse(self.puzzle.validate("WRONG"))
        self.assertFalse(self.puzzle.validate("TES"))
        self.assertFalse(self.puzzle.validate(""))


class TestEscapeRoomEnvironment(unittest.TestCase):
    """Test the EscapeRoomEnvironment class"""
    
    def setUp(self):
        self.env = EscapeRoomEnvironment(total_time_limit=300)
    
    def test_environment_initialization(self):
        """Test environment initializes correctly"""
        self.assertEqual(self.env.current_puzzle_idx, 0)
        self.assertEqual(self.env.total_time_limit, 300)
        self.assertIsNone(self.env.start_time)
        self.assertEqual(len(self.env.attempts_history), 0)
        self.assertEqual(self.env.hints_used, 0)
    
    def test_puzzles_created(self):
        """Test that puzzles are created"""
        puzzles = self.env.puzzles
        self.assertGreater(len(puzzles), 0)
        self.assertEqual(len(puzzles), 26)  # Should have 26 puzzles
        
        # Check each puzzle has required attributes
        for puzzle in puzzles:
            self.assertIsInstance(puzzle, Puzzle)
            self.assertIsNotNone(puzzle.id)
            self.assertIsNotNone(puzzle.name)
            self.assertIsNotNone(puzzle.description)
            self.assertIsNotNone(puzzle.correct_answer)
    
    def test_puzzle_answers_are_valid(self):
        """Test that all puzzle answers are non-empty"""
        for puzzle in self.env.puzzles:
            self.assertTrue(len(puzzle.correct_answer) > 0)
            self.assertNotEqual(puzzle.correct_answer.strip(), "")
    
    def test_start_timer(self):
        """Test that start() initializes the timer"""
        self.assertIsNone(self.env.start_time)
        self.env.start()
        self.assertIsNotNone(self.env.start_time)
        self.assertIsInstance(self.env.start_time, datetime)
    
    def test_get_current_puzzle(self):
        """Test getting current puzzle"""
        puzzle = self.env.get_current_puzzle()
        self.assertIsNotNone(puzzle)
        self.assertEqual(puzzle.id, 1)
    
    def test_get_current_puzzle_when_complete(self):
        """Test getting puzzle when all are solved"""
        self.env.current_puzzle_idx = len(self.env.puzzles)
        puzzle = self.env.get_current_puzzle()
        self.assertIsNone(puzzle)
    
    def test_time_remaining_before_start(self):
        """Test time remaining before game starts"""
        remaining = self.env.get_time_remaining()
        self.assertEqual(remaining, 300)
    
    def test_time_remaining_after_start(self):
        """Test time remaining after game starts"""
        self.env.start()
        time.sleep(1.5)  # Sleep longer to ensure time has passed
        remaining = self.env.get_time_remaining()
        self.assertLess(remaining, 300)
        self.assertGreaterEqual(remaining, 0)
    
    def test_submit_correct_answer(self):
        """Test submitting correct answer"""
        self.env.start()
        puzzle = self.env.get_current_puzzle()
        
        is_correct, feedback = self.env.submit_answer(puzzle.correct_answer, 1.0)
        
        self.assertTrue(is_correct)
        self.assertIn("CORRECT", feedback)
        self.assertEqual(self.env.current_puzzle_idx, 1)
        self.assertEqual(len(self.env.attempts_history), 1)
    
    def test_submit_incorrect_answer(self):
        """Test submitting incorrect answer"""
        self.env.start()
        
        is_correct, feedback = self.env.submit_answer("WRONG", 1.0)
        
        self.assertFalse(is_correct)
        self.assertIn("INCORRECT", feedback)
        self.assertEqual(self.env.current_puzzle_idx, 0)  # Should not advance
        self.assertEqual(len(self.env.attempts_history), 1)
    
    def test_get_hint(self):
        """Test getting hints"""
        initial_hints = self.env.hints_used
        hint = self.env.get_hint()
        
        self.assertIsNotNone(hint)
        self.assertIsInstance(hint, str)
        self.assertEqual(self.env.hints_used, initial_hints + 1)
    
    def test_hint_limit(self):
        """Test hint limit enforcement"""
        # Use all hints
        for _ in range(self.env.max_hints):
            hint = self.env.get_hint()
            self.assertIsNotNone(hint)
        
        # Try to get one more
        hint = self.env.get_hint()
        self.assertIsNone(hint)
    
    def test_is_complete_initially(self):
        """Test completion status at start"""
        self.assertFalse(self.env.is_complete())
    
    def test_is_complete_after_all_puzzles(self):
        """Test completion status after solving all puzzles"""
        self.env.current_puzzle_idx = len(self.env.puzzles)
        self.assertTrue(self.env.is_complete())
    
    def test_time_expiry(self):
        """Test time expiration check"""
        self.env.start()
        self.assertFalse(self.env.is_time_expired())
        
        # Simulate time expiry
        self.env.start_time = datetime.now() - timedelta(seconds=301)
        self.assertTrue(self.env.is_time_expired())
    
    def test_attempts_tracking(self):
        """Test that attempts are tracked correctly"""
        self.env.start()
        puzzle = self.env.get_current_puzzle()
        
        self.env.submit_answer("WRONG1", 1.0)
        self.env.submit_answer("WRONG2", 1.5)
        self.env.submit_answer(puzzle.correct_answer, 2.0)
        
        self.assertEqual(len(self.env.attempts_history), 3)
        self.assertFalse(self.env.attempts_history[0]['correct'])
        self.assertFalse(self.env.attempts_history[1]['correct'])
        self.assertTrue(self.env.attempts_history[2]['correct'])


class TestGeminiAgent(unittest.TestCase):
    """Test the GeminiAgent class"""
    
    def setUp(self):
        # Use a mock API key for testing
        self.mock_api_key = "test_api_key_12345"
    
    @patch('escape_room.genai.configure')
    @patch('escape_room.genai.GenerativeModel')
    def test_agent_initialization(self, mock_model, mock_configure):
        """Test agent initializes correctly"""
        agent = GeminiAgent(self.mock_api_key)
        
        mock_configure.assert_called_once_with(api_key=self.mock_api_key)
        mock_model.assert_called_once()
        self.assertEqual(len(agent.conversation_history), 0)
        self.assertEqual(len(agent.solved_answers), 0)
    
    @patch('escape_room.genai.configure')
    @patch('escape_room.genai.GenerativeModel')
    def test_extract_answer_with_answer_prefix(self, mock_model, mock_configure):
        """Test answer extraction with ANSWER: prefix"""
        agent = GeminiAgent(self.mock_api_key)
        
        response = """
        Reasoning: This is a test.
        ANSWER: Test Answer
        """
        
        answer = agent._extract_answer(response)
        self.assertEqual(answer, "Test Answer")
    
    @patch('escape_room.genai.configure')
    @patch('escape_room.genai.GenerativeModel')
    def test_extract_answer_without_prefix(self, mock_model, mock_configure):
        """Test answer extraction without ANSWER: prefix"""
        agent = GeminiAgent(self.mock_api_key)
        
        response = """
        This is reasoning.
        Final answer is here
        """
        
        answer = agent._extract_answer(response)
        self.assertEqual(answer, "Final answer is here")
    
    @patch('escape_room.genai.configure')
    @patch('escape_room.genai.GenerativeModel')
    def test_record_success(self, mock_model, mock_configure):
        """Test recording successful answers"""
        agent = GeminiAgent(self.mock_api_key)
        
        self.assertEqual(len(agent.solved_answers), 0)
        
        agent.record_success("Answer1")
        agent.record_success("Answer2")
        
        self.assertEqual(len(agent.solved_answers), 2)
        self.assertIn("Answer1", agent.solved_answers)
        self.assertIn("Answer2", agent.solved_answers)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def test_complete_puzzle_sequence(self):
        """Test solving all puzzles in sequence"""
        env = EscapeRoomEnvironment(total_time_limit=300)
        env.start()
        
        # Solve all puzzles with correct answers
        for i, puzzle in enumerate(env.puzzles):
            current = env.get_current_puzzle()
            self.assertIsNotNone(current)
            self.assertEqual(current.id, puzzle.id)
            
            is_correct, _ = env.submit_answer(puzzle.correct_answer, 1.0)
            self.assertTrue(is_correct)
            self.assertEqual(env.current_puzzle_idx, i + 1)
        
        self.assertTrue(env.is_complete())
    
    def test_puzzle_progression(self):
        """Test that puzzles progress correctly"""
        env = EscapeRoomEnvironment()
        env.start()
        
        # Check initial state
        self.assertEqual(env.current_puzzle_idx, 0)
        
        # Solve first puzzle
        puzzle1 = env.get_current_puzzle()
        env.submit_answer(puzzle1.correct_answer, 1.0)
        self.assertEqual(env.current_puzzle_idx, 1)
        
        # Solve second puzzle
        puzzle2 = env.get_current_puzzle()
        env.submit_answer(puzzle2.correct_answer, 1.0)
        self.assertEqual(env.current_puzzle_idx, 2)
    
    def test_final_puzzle_logic(self):
        """Test that the final puzzle uses previous answers correctly"""
        env = EscapeRoomEnvironment()
        
        # The final puzzle should require answers from previous puzzles
        final_puzzle = env.puzzles[-1]
        
        self.assertIn("previous", final_puzzle.description.lower())
        self.assertIsNotNone(final_puzzle.correct_answer)
        self.assertGreater(len(final_puzzle.correct_answer), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def test_empty_answer_submission(self):
        """Test submitting empty answer"""
        env = EscapeRoomEnvironment()
        env.start()
        
        is_correct, feedback = env.submit_answer("", 1.0)
        self.assertFalse(is_correct)
    
    def test_whitespace_answer_handling(self):
        """Test that whitespace is handled correctly"""
        env = EscapeRoomEnvironment()
        puzzle = env.get_current_puzzle()
        
        # Answer with extra whitespace should still work
        self.assertTrue(puzzle.validate(f"  {puzzle.correct_answer}  "))
    
    def test_case_insensitive_answers(self):
        """Test that answers are case insensitive"""
        env = EscapeRoomEnvironment()
        puzzle = env.get_current_puzzle()
        
        answer = puzzle.correct_answer
        self.assertTrue(puzzle.validate(answer.upper()))
        self.assertTrue(puzzle.validate(answer.lower()))
    
    def test_zero_time_limit(self):
        """Test environment with zero time limit"""
        env = EscapeRoomEnvironment(total_time_limit=0)
        env.start()
        
        self.assertTrue(env.is_time_expired())
    
    def test_negative_time_remaining(self):
        """Test that negative time is handled"""
        env = EscapeRoomEnvironment(total_time_limit=1)
        env.start()
        time.sleep(1.1)
        
        remaining = env.get_time_remaining()
        self.assertEqual(remaining, 0)  # Should not be negative


class TestPuzzleValidation(unittest.TestCase):
    """Test specific puzzle answers"""
    
    def test_cipher_puzzle(self):
        """Test the cipher puzzle answer"""
        env = EscapeRoomEnvironment()
        cipher_puzzle = env.puzzles[0]
        
        # ROT13 of "URYYB JBEYQ" should be "HELLO WORLD"
        self.assertTrue(cipher_puzzle.validate("HELLO WORLD"))
    
    def test_sequence_puzzle(self):
        """Test the sequence puzzle answer"""
        env = EscapeRoomEnvironment()
        sequence_puzzle = env.puzzles[1]
        
        # 2, 4, 8, 16, 32, ? = 64
        self.assertTrue(sequence_puzzle.validate("64"))
    
    def test_riddle_puzzle(self):
        """Test the riddle puzzle answer"""
        env = EscapeRoomEnvironment()
        riddle_puzzle = env.puzzles[2]
        
        # Echo riddle
        self.assertTrue(riddle_puzzle.validate("ECHO"))
    
    def test_anagram_puzzle(self):
        """Test the anagram puzzle answer"""
        env = EscapeRoomEnvironment()
        anagram_puzzle = env.puzzles[3]
        
        # OFREEDM = FREEDOM
        self.assertTrue(anagram_puzzle.validate("FREEDOM"))


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPuzzle))
    suite.addTests(loader.loadTestsFromTestCase(TestEscapeRoomEnvironment))
    suite.addTests(loader.loadTestsFromTestCase(TestGeminiAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestPuzzleValidation))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)