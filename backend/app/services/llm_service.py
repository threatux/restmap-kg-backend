"""
LLM Service — Qwen2.5 через Ollama.
Используется для:
  1. Генерация описания Rest Point
  2. AI-консьерж (чат-ассистент)
  3. Персонализированные рекомендации
"""
import httpx
import json
from typing import AsyncGenerator, List, Dict, Optional
from backend.app.core.config import settings


class LLMService:
    """Wrapper для Ollama API"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
    
    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Non-streaming generation"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(f"{self.base_url}/api/generate", json=payload)
                r.raise_for_status()
                data = r.json()
                return data.get("response", "").strip()
        except Exception as e:
            print(f"⚠️  LLM error: {e}")
            return ""
    
    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Streaming для чата"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as r:
                    async for line in r.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"⚠️  LLM stream error: {e}")
            yield ""
    
    # ============================================================
    # 🎯 GENERATE REST POINT CARD
    # ============================================================
    async def generate_rest_point_card(
        self,
        name: str,
        rest_point_type: str,
        coordinates: tuple,
        tourosat_score: float,
        insights: List[str],
        amenities: List[str] = None,
        language: str = "ru",
    ) -> Dict:
        """
        Генерирует полную карточку Rest Point.
        
        Returns:
            {
                "description": "...",
                "description_kg": "...",
                "description_en": "...",
                "services": [...],
                "tagline": "..."
            }
        """
        amenities_str = ", ".join(amenities) if amenities else "базовые удобства"
        insights_str = "\n  - ".join(insights[:5])
        
        system_prompt = """Ты — профессиональный копирайтер туристической платформы TamgaFlow в Кыргызстане.
Ты создаёшь красивые, эмоциональные описания для Rest Points (юрты, гестхаусы, эко-деревни) на Иссык-Куле.
ВСЕГДА возвращай ответ СТРОГО в формате JSON без объяснений, без markdown, без блоков ```."""
        
        user_prompt = f"""Создай карточку Rest Point для TamgaFlow.

📍 Название: {name}
🏠 Тип: {rest_point_type}
📌 Координаты: {coordinates[0]:.4f}, {coordinates[1]:.4f}
⭐ AI Score (TOUROSAT): {tourosat_score:.1f}/100
🎯 Особенности локации:
  - {insights_str}
🛋 Удобства: {amenities_str}

Верни ТОЛЬКО JSON строго в этом формате:
{{
  "tagline": "Короткий слоган (5-8 слов, цепляющий)",
  "description": "Описание на русском (100-150 слов, эмоциональное, с деталями природы)",
  "description_kg": "Описание на кыргызском (50-80 слов)",
  "description_en": "Description in English (80-120 words)",
  "services": [
    {{"name": "Юрта на 2 чел.", "price": 2500, "description": "Традиционная юрта с обогревом"}},
    {{"name": "Баня на дровах", "price": 1500, "description": "Настоящая баня 2 часа"}},
    {{"name": "Ужин с мясом", "price": 800, "description": "Бешбармак и чай"}},
    {{"name": "Прогулка на лошадях", "price": 1200, "description": "2-часовой тур"}}
  ]
}}

Используй красивые эмодзи в описании. Упомяни Иссык-Куль, горы, природу."""
        
        response = await self.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.8,
            max_tokens=2048,
        )
        
        # === Parse JSON ===
        try:
            # Очищаем если LLM вернул с markdown
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            return data
        except (json.JSONDecodeError, IndexError):
            # Fallback
            return {
                "tagline": f"Уникальный {rest_point_type} на Иссык-Куле",
                "description": f"🏔 {name} — идеальное место для отдыха на Иссык-Куле. "
                               f"AI TOUROSAT оценил эту локацию в {tourosat_score:.0f}/100 баллов. "
                               f"Окружённое природой место для настоящего релакса.",
                "description_kg": f"{name} — Ысык-Көлдөгү сонун жай.",
                "description_en": f"{name} is a unique spot on Issyk-Kul lake with AI score {tourosat_score:.0f}/100.",
                "services": [
                    {"name": "Юрта на 2 чел.", "price": 2500, "description": "Традиционная юрта"},
                    {"name": "Баня", "price": 1500, "description": "Баня 2 часа"},
                    {"name": "Ужин", "price": 800, "description": "Национальная кухня"},
                ],
            }


# Singleton
llm_service = LLMService()