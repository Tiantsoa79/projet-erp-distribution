"""
Client LLM multi-provider pour le reporting IA.

Supporte : OpenAI, Anthropic Claude, Google Gemini, LLM local (Ollama).
Si aucune cle API n'est configuree, le module fonctionne en mode
"fallback" avec des analyses statistiques pures (sans IA).
"""

import os
import json
import requests
from typing import Dict, List, Optional


class LLMClient:
    """Client unifie pour appeler differents providers LLM."""

    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "openai")
        self.providers = {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": "https://api.openai.com/v1",
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            },
            "claude": {
                "api_key": os.getenv("CLAUDE_API_KEY", ""),
                "base_url": "https://api.anthropic.com/v1",
                "model": os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229"),
            },
            "gemini": {
                "api_key": os.getenv("GEMINI_API_KEY", ""),
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            },
            "local": {
                "api_key": "",
                "base_url": os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1"),
                "model": os.getenv("LOCAL_LLM_MODEL", "llama2"),
            },
        }

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """Verifie si un provider IA est configure et accessible."""
        cfg = self.providers.get(self.provider, {})
        if self.provider == "local":
            return self._test_local(cfg)
        return bool(cfg.get("api_key"))

    def get_status(self) -> Dict:
        """Retourne le statut de chaque provider."""
        status = {}
        for name, cfg in self.providers.items():
            if name == "local":
                status[name] = {"configured": True, "has_key": True}
            else:
                status[name] = {
                    "configured": bool(cfg["api_key"]),
                    "has_key": bool(cfg["api_key"]),
                }
        status["active_provider"] = self.provider
        status["ai_available"] = self.is_available()
        return status

    # ------------------------------------------------------------------
    def chat(self, messages: List[Dict], temperature: float = 0.7,
             max_tokens: int = 2000) -> Optional[str]:
        """Envoie une requete chat au provider actif."""
        cfg = self.providers.get(self.provider)
        if not cfg:
            return None

        try:
            if self.provider == "openai":
                return self._call_openai(cfg, messages, temperature, max_tokens)
            elif self.provider == "claude":
                return self._call_claude(cfg, messages, temperature, max_tokens)
            elif self.provider == "gemini":
                return self._call_gemini(cfg, messages, temperature, max_tokens)
            elif self.provider == "local":
                return self._call_local(cfg, messages, temperature, max_tokens)
        except Exception as exc:
            print(f"[ai] Erreur appel {self.provider}: {exc}")
            return None

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _call_openai(self, cfg, messages, temperature, max_tokens):
        if not cfg["api_key"]:
            return None
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        }
        data = {
            "model": cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = requests.post(
            f"{cfg['base_url']}/chat/completions",
            headers=headers, json=data, timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        print(f"[ai/openai] HTTP {resp.status_code}: {resp.text[:200]}")
        return None

    def _call_claude(self, cfg, messages, temperature, max_tokens):
        if not cfg["api_key"]:
            return None
        headers = {
            "x-api-key": cfg["api_key"],
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        data = {
            "model": cfg["model"],
            "max_tokens": max_tokens,
            "messages": messages,
        }
        resp = requests.post(
            f"{cfg['base_url']}/messages",
            headers=headers, json=data, timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
        print(f"[ai/claude] HTTP {resp.status_code}: {resp.text[:200]}")
        return None

    def _call_gemini(self, cfg, messages, temperature, max_tokens):
        if not cfg["api_key"]:
            return None
        
        # Convert messages to Gemini format
        import google.genai as genai
        
        try:
            # Convert messages to Gemini prompt format
            prompt = ""
            for msg in messages:
                if msg["role"] == "system":
                    prompt += f"System: {msg['content']}\n\n"
                elif msg["role"] == "user":
                    prompt += f"User: {msg['content']}\n\n"
                elif msg["role"] == "assistant":
                    prompt += f"Assistant: {msg['content']}\n\n"
            
            client = genai.Client(api_key=cfg["api_key"])
            response = client.models.generate_content(
                model=cfg["model"],
                contents=prompt
            )
            
            return response.text
            
        except Exception as exc:
            print(f"[ai/gemini] Erreur: {exc}")
            return None

    def _call_local(self, cfg, messages, temperature, max_tokens):
        headers = {"Content-Type": "application/json"}
        data = {
            "model": cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = requests.post(
            f"{cfg['base_url']}/chat/completions",
            headers=headers, json=data, timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return None

    def _test_local(self, cfg) -> bool:
        try:
            resp = requests.get(f"{cfg['base_url']}/models", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False
