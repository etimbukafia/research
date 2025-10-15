import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from rag import SimpleRAG
from agents.react_agent import AdvancedReactAgent 
from agents.verifier_agent import VerifierAgent 
from utils.memory import MemoryLayer
from utils.prompt_manager import PromptManager, PromptType
from pathlib import Path

load_dotenv()

def save_output_to_json(query, mode, use_verifier, use_memory, result):
    """Saving query results to JSON file in output folder."""
    # Creating output folder if it doesn't exist
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Creating flags string
    flags = []
    if use_verifier:
        flags.append("verify")
    if use_memory:
        flags.append("memory")
    flag_str = "_".join(flags) if flags else "no_flags"
    
    # Creating filename with sanitized query
    query_snippet = "".join(c if c.isalnum() else "_" for c in query[:10])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_{query_snippet}_{flag_str}_{timestamp}.json"
    filepath = output_dir / filename
    
    # Extracting structured data from steps
    steps = result.get("steps", [])
    reasoning_steps = []
    thoughts = []
    actions = []
    observations = []
    conclusions = []
    
    for i, step in enumerate(steps, 1):
        step_data = {
            "step_number": i,
            "thought": step.get("thought", ""),
            "action": step.get("action", "none"),
            "action_input": step.get("action_input", ""),
            "observation": step.get("observation", ""),
            "final_answer": step.get("final_answer", "")
        }
        reasoning_steps.append(step_data)
        
        # Collecting individual components
        if step.get("thought"):
            thoughts.append({"step": i, "content": step["thought"]})
        if step.get("action") and step.get("action") != "none":
            actions.append({
                "step": i, 
                "action": step["action"],
                "input": step.get("action_input", "")
            })
        if step.get("observation"):
            observations.append({"step": i, "content": step["observation"]})
        if step.get("final_answer"):
            conclusions.append({"step": i, "content": step["final_answer"]})
    
    # Preparing output data
    output_data = {
        "metadata": {
            "query": query,
            "mode": mode.value if hasattr(mode, 'value') else str(mode),
            "flags": {
                "verifier": use_verifier,
                "memory": use_memory
            },
            "timestamp": datetime.now().isoformat(),
            "iterations": result.get("iterations", 0),
            "success": result.get("success", False)
        },
        "execution": {
            "reasoning_steps": reasoning_steps,
            "thoughts": thoughts,
            "actions": actions,
            "observations": observations,
            "conclusions": conclusions
        },
        "verification": result.get("verification", None),
        "answer": result.get("answer", ""),
        "raw_result": result
    }
    
    # Writing to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Output saved to: {filepath}")
    return filepath
    
def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not found in .env file")
        sys.exit(1)
    
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        print("❌ Error: TAVILY_API_KEY not found in .env file")
        sys.exit(1)
    
    rag = SimpleRAG(
        api_key=api_key,
        tavily_api_key=tavily_api_key,
        papers_folder="./papers",
        chroma_db_path=Path(__file__).parent / "chroma_db"
    )
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py ingest              - Ingesting PDF papers")
        print("  python main.py delete              - Deleting database")
        print("  python main.py check               - Checking database")
        print("  python main.py query 'question'    - Querying the system")
        print("\nQuery flags:")
        print("  --verify                           - Enabling verification")
        print("  --memory                           - Enabling memory")
        print("  --mode [base|advanced_react|pddl]  - Setting prompt mode (default: base)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Ingesting papers
    if command == "ingest":
        print("📚 Ingesting papers...")
        rag.ingest_papers()
        print("✅ Ingestion complete!")
    
    # Deleting database
    elif command == "delete":
        print("🗑️  Deleting database...")
        rag.reset_database()
        print("✅ Database deleted!")
    
    # Checking database
    elif command == "check":
        try:
            count = rag.collection.count()
            print(f"📊 Documents in collection: {count}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Querying system
    elif command == "query":
        if len(sys.argv) < 3:
            print("❌ Please provide a question")
            sys.exit(1)
        
        question = sys.argv[2]
        
        # Parsing flags
        use_verifier = "--verify" in sys.argv
        use_memory = "--memory" in sys.argv
        
        # Getting and validating mode
        mode_str = "base"
        if "--mode" in sys.argv:
            mode_idx = sys.argv.index("--mode")
            if mode_idx + 1 < len(sys.argv):
                mode_str = sys.argv[mode_idx + 1].lower()
        
        # Validating and converting mode string to PromptType
        try:
            mode = PromptType(mode_str)
        except ValueError:
            valid_modes = [m.value for m in PromptType]
            print(f"❌ Invalid mode '{mode_str}'. Valid modes: {', '.join(valid_modes)}")
            sys.exit(1)
        
        print(f"🎯 Using '{mode.value}' mode")
        
        # Initializing PromptManager with selected mode
        prompts = PromptManager(debug=True)
        prompts._setup_prompts(mode=mode)
        
        # Setting up plugins
        verifier = VerifierAgent(api_key) if use_verifier else None
        memory = MemoryLayer() if use_memory else None
        
        # Creating agent
        agent = AdvancedReactAgent(
            api_key=api_key,
            tools=rag.tools,
            verifier=verifier,
            memory=memory,
            prompt_manager=prompts
        )
        
        # Running query
        print(f"❓ Question: {question}")
        print(f"🔍 Verifier: {'ON' if use_verifier else 'OFF'}")
        print(f"💾 Memory: {'ON' if use_memory else 'OFF'}\n")
        
        result = agent.run(
            question,
            use_verifier=use_verifier,
            use_memory=use_memory
        )
        
        # Saving output to JSON
        save_output_to_json(
            query=question,
            mode=mode,
            use_verifier=use_verifier,
            use_memory=use_memory,
            result=result
        )
        
        print("\n" + "="*60)
        print("📝 ANSWER:")
        print("="*60)
        print(result["answer"])
        print("\n" + "="*60)
        print(f"✅ Completed in {result['iterations']} iterations")
        if result.get("verification"):
            print(f"🔍 Verdict: {result['verification'].get('verdict')}")
        print("="*60)
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()