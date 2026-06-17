from config import PROVIDER, GROQ_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY


def get_client():
    """Return the right LLM client based on the PROVIDER set in config."""
    if PROVIDER == "groq":
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)
    elif PROVIDER == "openai":
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY)
    elif PROVIDER == "anthropic":
        from anthropic import Anthropic
        return Anthropic(api_key=ANTHROPIC_API_KEY)
    else:
        raise ValueError(f"Unknown provider: '{PROVIDER}'. Choose groq, openai, or anthropic.")