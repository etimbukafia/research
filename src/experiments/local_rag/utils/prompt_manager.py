from pathlib import Path
import re
import logging
from enum import Enum
from typing import Optional, Dict

logger = logging.getLogger("prompt_manager")
logging.basicConfig(level=logging.INFO)


class PromptType(str, Enum):
    BASE = "base"
    ADVANCED_REACT = "advanced_react"
    PDDL = "pddl"


class PromptManager:
    """Centralized prompt management for dynamic multi-layer prompting."""

    def __init__(self, prompts_dict: Optional[Dict] = None, debug: bool = True):
        self.prompts = prompts_dict or {}
        self.debug = debug
        self._setup_prompts()

    def _setup_prompts(self, mode: Optional[PromptType] = None):
        """Setting up prompts based on mode."""
        self.active_mode = mode
        base_dir = Path(__file__).parent.resolve()
        prompts_dir = base_dir.parent / "prompts" / "nl"

        if self.debug:
            print(f"[DEBUG] Base path: {base_dir}")
            print(f"[DEBUG] Expected prompts directory: {prompts_dir.resolve()}")

        try:
            nl_prompts = self.get_nl_prompts()
            
            if mode == PromptType.BASE:
                self.prompts["base"] = nl_prompts.get("base", "")
                if self.debug and nl_prompts.get("base"):
                    print("✅ Loaded base NL prompt successfully.\n")
                    
            elif mode == PromptType.ADVANCED_REACT:
                self.prompts["advanced_react"] = nl_prompts.get("advanced_react", "")
                if self.debug and nl_prompts.get("advanced_react"):
                    print("✅ Loaded advanced ReAct NL prompt successfully.\n")
                    
            elif mode == PromptType.PDDL:
                self.prompts["base"] = nl_prompts.get("base", "")
                self.prompts["domain_prompt"] = nl_prompts.get("domain_prompt", "")
                self.prompts["problem_prompt"] = nl_prompts.get("problem_prompt", "")
                
                if self.prompts["domain_prompt"] and self.prompts["problem_prompt"]:
                    self.prompts["pddl"] = (
                        self.prompts["domain_prompt"] + "\n\n" + self.prompts["problem_prompt"]
                    )
                    if self.debug:
                        print("✅ Loaded PDDL prompts successfully.\n")
                else:
                    logger.warning("PDDL prompts incomplete - missing domain or problem prompt")
                    
        except Exception as e:
            logger.error(f"⚠️ Error loading prompts: {e}")

    def get_nl_prompts(self) -> Dict[str, str]:
        """Loading natural language prompts from files."""
        prompts_dir = Path(__file__).parent.parent / "prompts" / "nl"

        if self.debug:
            print(f"[DEBUG] Loading NL prompts from: {prompts_dir.resolve()}")

        # Defining prompt files
        prompt_files = {
            "domain_prompt": "domain_nl.txt",
            "problem_prompt": "problem_nl.txt",
            "base": "base.txt",
            "advanced_react": "advanced_react.txt"
        }

        result = {}

        for key, filename in prompt_files.items():
            file_path = prompts_dir / filename
            
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding="utf-8") as f:
                        content = f.read().strip()
                        
                    # Applying markdown cleaning only to PDDL prompts
                    if key in ["domain_prompt", "problem_prompt"]:
                        content = self._clean_markdown(content)
                        
                    result[key] = content
                    
                except Exception as e:
                    logger.error(f"Error reading {filename}: {e}")
                    result[key] = ""
            else:
                logger.warning(f"{key} not found at {file_path}")
                result[key] = ""

        return result

    def _clean_markdown(self, text: str) -> str:
        """Removing Markdown formatting."""
        text = re.sub(r"#+", "", text)  # Remove headings
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Remove bold
        text = re.sub(r"`+", "", text)  # Remove code ticks
        return text.strip()

    def get_prompt(self, name: str, **kwargs) -> str:
        """Getting prompt with variable substitution."""
        template = self.prompts.get(name, "")
        
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            template = template.replace(placeholder, str(value))
            
        return template

    def add_prompt(self, name: str, template: str):
        """Adding or updating a prompt template."""
        self.prompts[name] = template

    def compose_prompt(
        self, 
        query: str, 
        tools: dict, 
        prompt_type: Optional[PromptType] = None
    ) -> str:
        """Composing final structured prompt with isolated PDDL context."""
        # Preparing variables for substitution
        tools_description = "\n".join(
            [f"- {t.name}: {t.description}" for t in tools.values()]
        )
        
        variables = {
            "query": query,
            "tools": tools_description
        }

        # Getting prompts with variable substitution
        base = self.get_prompt("base", **variables)
        advanced_react = self.get_prompt("advanced_react", **variables)
        pddl = self.prompts.get("pddl")

        # Handling different prompt types
        if prompt_type in (PromptType.BASE, "base"):
            logger.info("Using base prompt")
            return base.strip() if base else ""
        
        if prompt_type in (PromptType.ADVANCED_REACT, "advanced_react"):
            logger.info("Using advanced ReAct prompt")
            return advanced_react.strip() if advanced_react else base.strip()
        
        if prompt_type in (PromptType.PDDL, "pddl"):
            logger.info("Using PDDL prompt with context isolation")
            # Checking if we have all required components
            if not all([base, pddl]):
                logger.warning("Incomplete PDDL prompt components, falling back to base")
                return base.strip() if base else ""
            
            # Context isolation with proper formatting
            context = f"{pddl}".strip()
            composed = f"""{base}

---
The following content describes the system's internal logic and task background.
You must use it **only to inform your reasoning** — do not copy or restate it.

{context}

---
Now begin reasoning and respond **strictly in valid JSON** according to the earlier format.
If you need to reason, put all internal thoughts in the "thought" field.
"""
            return composed.strip()
        
        # Default fallback
        logger.warning(f"Unknown prompt_type: {prompt_type}, using base")
        return base.strip() if base else ""

    def show_prompt_paths(self):
        """Displaying all known prompt file locations and loaded keys."""
        print("\n🧭 PromptManager Debug Info")
        base_dir = Path(__file__).parent.resolve()
        prompts_dir = base_dir.parent / "prompts" / "nl"
        
        print(f"  Base path: {base_dir}")
        print(f"  Prompts directory: {prompts_dir.resolve()}")

        print("\n🗂️ Loaded prompt keys:")
        if self.prompts:
            for key in self.prompts.keys():
                preview = self.prompts[key][:50] + "..." if len(self.prompts[key]) > 50 else self.prompts[key]
                print(f"   - {key}: {preview}")
        else:
            print("   (none loaded)")

        print("\n📜 Available .txt files:")
        if prompts_dir.exists():
            txt_files = list(prompts_dir.glob("*.txt"))
            if txt_files:
                for f in txt_files:
                    print(f"   - {f.name}")
            else:
                print("   (no .txt files found)")
        else:
            print("   ⚠️ prompts/nl directory does not exist.")
        print()