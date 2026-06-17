from groq import Groq
import google.generativeai as genai
from openai import OpenAI
import anthropic


def get_llm_response(provider: str, api_key: str, system_prompt: str, user_prompt: str) -> str:
    """
    Llama al LLM seleccionado y devuelve la respuesta como texto.
    Soporta: groq, openai, gemini, anthropic
    """
    try:
        if provider == "groq":
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2000
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
                temperature=0.2,
                max_tokens=2000
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
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return response.content[0].text

        else:
            return ""

    except Exception as e:
        raise RuntimeError(f"Error llamando al LLM ({provider}): {str(e)}")
