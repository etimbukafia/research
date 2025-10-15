import os
import json
import requests
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.resolve()


# ---------- CONFIG ----------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

DOMAIN_PATH = BASE_DIR / "prompts" / "pddl" / "domain.pddl"
PROBLEM_TEMPLATE_PATH = BASE_DIR / "prompts" / "pddl" / "problem.pddl"

DOMAIN_NL_PATH = BASE_DIR / "prompts" / "nl" / "domain_nl.txt"
PROBLEM_NL_PATH = BASE_DIR / "prompts" / "nl" / "problem_nl.txt"

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")


def send_to_gemini(prompt: str) -> str:
    try:
        response = model.generate_content(
            prompt,
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=1024,
                temperature=0.2,
                top_p=0.8,
                top_k=40,
                stop_sequences=["--- END ---"]
            )
        )
    except Exception as e:
        return f"Error from Gemini API: {e}"
    return response.text

# ---------- PROMPT TEMPLATES ----------
with open(BASE_DIR / "prompts" / "nl" / "domain_converter.txt", 'r', encoding="utf-8") as f:
    DOMAIN_PROMPT = f.read()


with open(BASE_DIR / "prompts" / "nl" / "problem_converter.txt", 'r', encoding="utf-8") as f:
    PROBLEM_PROMPT = f.read()


# ---------- CONVERSION ----------
def convert_and_store():
    print("🔹 Converting domain.pddl...")
    domain_text = DOMAIN_PATH.read_text(encoding="utf-8")
    domain_prompt = DOMAIN_PROMPT.format(domain=domain_text)
    domain_nl = send_to_gemini(domain_prompt)
    DOMAIN_NL_PATH.write_text(domain_nl, encoding="utf-8")

    print("🔹 Converting problem_template.pddl...")
    problem_text = PROBLEM_TEMPLATE_PATH.read_text(encoding="utf-8")
    problem_prompt = PROBLEM_PROMPT.replace("{problem}", problem_text)
    problem_nl = send_to_gemini(problem_prompt)
    PROBLEM_NL_PATH.write_text(problem_nl, encoding="utf-8")

    print("✅ Conversion complete. Files saved:")
    print(f"   - {DOMAIN_NL_PATH}")
    print(f"   - {PROBLEM_NL_PATH}")

# ---------- MAIN ----------
if __name__ == "__main__":
    convert_and_store()
