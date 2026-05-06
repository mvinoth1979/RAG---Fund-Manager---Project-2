import os
import logging
from typing import Tuple
import groq
import google.generativeai as genai

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Groq Setup
        self.groq_client = None
        if self.groq_api_key:
            self.groq_client = groq.Groq(api_key=self.groq_api_key)
            
        # Gemini Setup
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            
        self.groq_primary = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.groq_secondary = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")
        self.gemini_primary = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
        self.temperature = 0.0
        self.max_tokens = 150
        self.timeout = 10.0 # 10 seconds

    def _call_groq(self, model: str, system: str, user: str) -> str:
        if not self.groq_client:
            raise ValueError("Groq API key not configured")
            
        response = self.groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=1.0,
            seed=42,
            timeout=self.timeout
        )
        return response.choices[0].message.content

    def _call_gemini(self, model_name: str, system: str, user: str) -> str:
        if not self.gemini_api_key:
            raise ValueError("Gemini API key not configured")
            
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system
        )
        
        response = model.generate_content(
            user,
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                top_p=1.0
            ),
            request_options={"timeout": self.timeout}
        )
        return response.text

    def _call_ollama(self, system: str, user: str) -> str:
        # Fallback to local ollama
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama3.1:8b",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "top_p": 1.0,
                    "seed": 42
                }
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def generate(self, system: str, user: str) -> Tuple[str, str]:
        """
        Attempts inference according to failover order:
        Groq Primary -> Groq Secondary -> Gemini -> Ollama
        Returns (response_text, provider_used)
        """
        exceptions = []
        
        # 1. Groq Primary
        try:
            logger.info(f"Attempting Groq primary ({self.groq_primary})")
            return self._call_groq(self.groq_primary, system, user), f"groq:{self.groq_primary}"
        except Exception as e:
            logger.warning(f"Groq primary failed: {e}")
            exceptions.append(str(e))
            
        # 2. Groq Secondary
        try:
            logger.info(f"Attempting Groq secondary ({self.groq_secondary})")
            return self._call_groq(self.groq_secondary, system, user), f"groq:{self.groq_secondary}"
        except Exception as e:
            logger.warning(f"Groq secondary failed: {e}")
            exceptions.append(str(e))
            
        # 3. Gemini Primary
        try:
            logger.info(f"Attempting Gemini primary ({self.gemini_primary})")
            return self._call_gemini(self.gemini_primary, system, user), f"gemini:{self.gemini_primary}"
        except Exception as e:
            logger.warning(f"Gemini primary failed: {e}")
            exceptions.append(str(e))
            
        # 4. Ollama Local
        try:
            logger.info("Attempting Ollama local (llama3.1:8b)")
            return self._call_ollama(system, user), "ollama:llama3.1:8b"
        except Exception as e:
            logger.error(f"Ollama fallback failed: {e}")
            exceptions.append(str(e))
            
        raise RuntimeError(f"All LLM providers failed. Exceptions: {exceptions}")
