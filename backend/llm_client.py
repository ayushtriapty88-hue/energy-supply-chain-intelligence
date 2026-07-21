import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "llama3.2"
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")

def _try_ollama(prompt, system_prompt=""):
    """Try Ollama first — free, local, no internet needed."""
    try:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = requests.post(
            OLLAMA_URL,
            json={
                "model":  OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
            },
            timeout=120,
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception:
        pass
    return None

def _try_claude(prompt, system_prompt=""):
    """Fall back to Claude API if Ollama not available."""
    if not ANTHROPIC_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        kwargs = {
            "model":      "claude-sonnet-4-6",
            "max_tokens": 1000,
            "messages":   [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        response = client.messages.create(**kwargs)
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  [Claude API] Error: {e}")
    return None

def ask_llm(prompt, system_prompt="", verbose=True):
    """
    Universal LLM caller.
    Tries Ollama first (free), falls back to Claude API automatically.
    All agents in this project use this single function.
    """
    # Try Ollama first
    result = _try_ollama(prompt, system_prompt)
    if result:
        if verbose:
            print("  [LLM] Using Ollama (local)")
        return result

    # Fall back to Claude API
    if verbose:
        print("  [LLM] Ollama unavailable — using Claude API")
    result = _try_claude(prompt, system_prompt)
    if result:
        return result

    # Both failed
    if verbose:
        print("  [LLM] Both LLM options failed")
    return None

def ask_llm_json(prompt, system_prompt="", verbose=True):
    """
    Same as ask_llm but cleans response and parses JSON.
    Use this whenever you need structured output.
    """
    system_with_json = (system_prompt or "") + \
        "\nYou must respond ONLY with valid JSON. No explanation, " \
        "no markdown, no code blocks. Raw JSON only."

    raw = ask_llm(prompt, system_with_json, verbose)
    if not raw:
        return None

    # Clean up common LLM JSON formatting issues
    cleaned = raw.strip()
    # Remove markdown code blocks if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        start = cleaned.find("{")
        end   = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except Exception:
                pass
        if verbose:
            print(f"  [LLM] JSON parse failed. Raw: {cleaned[:100]}...")
        return None

if __name__ == "__main__":
    print("Testing LLM client...\n")

    # Test 1 — plain text
    print("[Test 1] Plain text response:")
    result = ask_llm("In one sentence, what is the Strait of Hormuz?")
    print(f"  Result: {result}\n")

    # Test 2 — JSON response
    print("[Test 2] JSON response:")
    result = ask_llm_json(
        "Give me a JSON object with keys 'corridor' and 'risk_level' "
        "for the Strait of Hormuz today."
    )
    print(f"  Result: {result}\n")

    if result:
        print("✓ LLM client working correctly")
    else:
        print("✗ LLM client failed — check Ollama or API key")