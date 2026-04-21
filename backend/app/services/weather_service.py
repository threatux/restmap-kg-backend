"""
Weather service — Open-Meteo API (бесплатный, без ключа)
"""
import httpx
from typing import Dict, Optional
from backend.app.core.config import settings


class WeatherService:
    
    @staticmethod
    async def get_current_weather(lat: float, lon: float) -> Optional[Dict]:
        """Текущая погода + прогноз"""
        url = settings.OPEN_METEO_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max",
            "timezone": "Asia/Bishkek",
            "forecast_days": 3,
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, params=params)
                r.raise_for_status()
                data = r.json()
                
                current = data.get("current", {})
                daily = data.get("daily", {})
                
                return {
                    "current": {
                        "temperature": current.get("temperature_2m"),
                        "feels_like": current.get("apparent_temperature"),
                        "humidity": current.get("relative_humidity_2m"),
                        "wind_speed": current.get("wind_speed_10m"),
                        "condition": WeatherService._code_to_text(current.get("weather_code", 0)),
                        "icon": WeatherService._code_to_emoji(current.get("weather_code", 0)),
                    },
                    "forecast": [
                        {
                            "date": daily.get("time", [])[i] if daily.get("time") else None,
                            "temp_max": daily.get("temperature_2m_max", [])[i] if daily.get("temperature_2m_max") else None,
                            "temp_min": daily.get("temperature_2m_min", [])[i] if daily.get("temperature_2m_min") else None,
                            "condition": WeatherService._code_to_text(daily.get("weather_code", [])[i] if daily.get("weather_code") else 0),
                            "icon": WeatherService._code_to_emoji(daily.get("weather_code", [])[i] if daily.get("weather_code") else 0),
                        }
                        for i in range(min(3, len(daily.get("time", []))))
                    ],
                }
        except Exception as e:
            print(f"⚠️  Weather API error: {e}")
            return {
                "current": {"temperature": 18, "condition": "Ясно", "icon": "☀️"},
                "forecast": [],
            }
    
    @staticmethod
    def _code_to_text(code: int) -> str:
        codes = {
            0: "Ясно", 1: "Преимущественно ясно", 2: "Переменная облачность", 3: "Пасмурно",
            45: "Туман", 51: "Моросит", 61: "Дождь", 63: "Дождь", 71: "Снег", 95: "Гроза",
        }
        return codes.get(code, "Переменная")
    
    @staticmethod
    def _code_to_emoji(code: int) -> str:
        if code == 0: return "☀️"
        if code in [1, 2]: return "🌤"
        if code == 3: return "☁️"
        if code in [45, 48]: return "🌫"
        if code in [51, 53, 55, 61, 63, 65]: return "🌧"
        if code in [71, 73, 75, 77, 85, 86]: return "❄️"
        if code in [95, 96, 99]: return "⛈"
        return "🌤"