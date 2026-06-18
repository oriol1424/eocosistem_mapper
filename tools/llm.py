from groq import Groq
import google.generativeai as genai
from openai import OpenAI
import anthropic

GROQ_MODEL_SMALL = "llama-3.1-8b-instant"
GROQ_MODEL_LARGE = "llama-3.3-70b-versatile"


def get_llm_response(provider: str, api_key: str, system_prompt: str, user_prompt: str, use_large: bool = False) -> str:
    """
    Llama al LLM seleccionado. Por defecto usa modelo pequeño para ahorrar tokens.
    use_large=True solo para la llamada final de enriquecimiento.
    """
    try:
        if provider == "groq":
            model = GROQ_MODEL_LARGE if use_large else GROQ_MODEL_SMALL
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            return response.choices[0].message.content

        elif provider == "openai":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            return response.choices[0].message.content

        elif provider == "gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_prompt
            )
            response = model.generate_content(user_prompt)
            return response.text

        elif provider == "anthropic":
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return response.content[0].text

        else:
            return ""

    except Exception as e:
        raise RuntimeError(f"Error llamando al LLM ({provider}): {str(e)}")
