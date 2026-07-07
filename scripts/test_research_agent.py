import sys
import os
from dotenv import load_dotenv

# Ensure the parent directory (backend root) is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env variables before importing agent modules
load_dotenv()

from agents.research_agent import run_research

def main():
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = "Latest developments in the EV battery market in 2026"
    
    print(f"Starting research on topic: {topic}\n")
    try:
        result = run_research(topic)
        print("\n" + "="*50)
        print("RESEARCH RESULT:")
        print("="*50)
        print(result)
    except ValueError as e:
        print(f"\nConfiguration Error: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == '__main__':
    # To run this script, use the following command from the backend folder:
    # python -m scripts.test_research_agent
    main()
