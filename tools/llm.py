from groq import Groq
import google.generativeai as genai
from openai import OpenAI
import anthropic
import time
import threading
import re as _re

_last_groq_call = [0.0]
_groq_lock = threading.Lock()

GROQ_MODEL_SMALL = "llama-3.1-8b-instant"
GROQ_MODEL_LARGE = "llama-3.3-70b-versatile"


def _groq_throttle():
    """Pausa mínima entre llamadas a Groq."""
    with _groq_lock:
        elapsed = time.time() - _last_groq_call[0]
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _last_groq_call[0] = time.time()


def _extraer_espera_groq(mensaje_error: str) -> float:
    """Extrae el tiempo de espera del mensaje 429 de Groq y añade 1s extra."""
    try:
        # Formato: "try again in 2.18s"
        match = _re.search(r"try again in ([\d.]+)s", mensaje_error)
        if match:
            return float(match.group(1)) + 1.0
        # Formato: "try again in 1m5.3s"
        match = _re.search(r"try again in ([\d]+)m([\d.]+)s", mensaje_error)
        if match:
            return float(match.group(1)) * 60 + float(match.group(2)) + 1.0
    except Exception:
        pass
    return 5.0


def get_llm_response(provider: str, api_key: str, system_prompt: str,
                     user_prompt: str, use_large: bool = False) -> str:
    """
    Llama al LLM seleccionado. Por defecto usa modelo pequeño para ahorrar tokens.
    Para Groq: reintenta automáticamente si hay rate limit, esperando el tiempo indicado.
    """
    try:
        if provider == "groq":
            _groq_throttle()
            model = GROQ_MODEL_LARGE if use_large else GROQ_MODEL_SMALL
            client = Groq(api_key=api_key)
            for intento in range(4):
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=1500
                    )
                    _last_groq_call[0] = time.time()
                    return response.choices[0].message.content
                except Exception as e:
                    msg = str(e)
                    if "429" in msg or "rate_limit" in msg.lower():
                        espera = _extraer_espera_groq(msg)
                        time.sleep(espera)
                        continue
                    raise
            raise RuntimeError("Groq: límite de rate alcanzado tras varios reintentos")

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
