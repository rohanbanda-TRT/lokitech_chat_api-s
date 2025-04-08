"""
Test script for the Coaching History Analyzer
"""

import os
from dotenv import load_dotenv
from app.src.agents.coaching_history_analyzer import CoachingHistoryAnalyzer

def test_coaching_analyzer():
    """
    Test the Coaching History Analyzer with different scenarios
    """
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    # Path to coaching data
    coaching_data_path = os.path.join(os.getcwd(), "coaching_history.json")
    if not os.path.exists(coaching_data_path):
        coaching_data_path = os.path.join(os.getcwd(), "Coaching Details.xlsx")
    
    print(f"Using coaching data from: {coaching_data_path}")
    
    # Initialize the analyzer
    analyzer = CoachingHistoryAnalyzer(api_key, coaching_data_path)
    
    # Test cases
    test_cases = [
        {
            "employee_name": "Moises",
            "coaching_category": "Speeding Violations",
            "coaching_reason": "Moises was cited for a speeding violation while operating a company vehicle."
        },
        {
            "employee_name": "Moises",
            "coaching_category": "Hard Braking",
            "coaching_reason": "Moises was cited for hard braking while operating a company vehicle."
        },
        {
            "employee_name": "Moises",
            "coaching_category": "Following Distance",
            "coaching_reason": "Moises was cited for not maintaining proper following distance."
        }
    ]
    
    # Run tests
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\nTest Case {i}: {test_case['employee_name']} - {test_case['coaching_category']}")
        print("=" * 80)
        
        result = analyzer.analyze_coaching_history(
            test_case["employee_name"],
            test_case["coaching_category"],
            test_case["coaching_reason"]
        )
        
        print(result)
        print("=" * 80)

if __name__ == "__main__":
    test_coaching_analyzer()
