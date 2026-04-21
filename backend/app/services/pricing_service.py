"""
Dynamic Pricing — цена зависит от TOUROSAT score.
"""
from datetime import date
from dataclasses import dataclass
from backend.app.core.config import settings


@dataclass
class PricingResult:
    base_price: float
    final_price: float
    multiplier: float
    factors: dict
    
    def to_dict(self):
        return {
            "base_price_kgs": round(self.base_price, 2),
            "final_price_kgs": round(self.final_price, 2),
            "multiplier": round(self.multiplier, 2),
            "factors": self.factors,
        }


class PricingService:
    """
    Динамическое ценообразование.
    Формула:
      final_price = base_price × score_multiplier × seasonal_multiplier × demand_multiplier
    """
    
    @staticmethod
    def calculate_price(base_price: float, tourosat_score: float,
                       check_in: date = None, competitors_count: int = 5) -> PricingResult:
        
        # === 1. Множитель по TOUROSAT Score ===
        if tourosat_score >= 80:
            score_mult = settings.PRICING_SCORE_80_PLUS_MULTIPLIER  # +30%
            score_label = "Топ-локация"
        elif tourosat_score >= 60:
            score_mult = settings.PRICING_SCORE_60_79_MULTIPLIER  # base
            score_label = "Хорошая локация"
        else:
            score_mult = settings.PRICING_SCORE_BELOW_60_MULTIPLIER  # -20%
            score_label = "Средняя локация"
        
        # === 2. Сезонность ===
        seasonal_mult = 1.0
        season_label = "Стандартный сезон"
        if check_in:
            month = check_in.month
            if month in [6, 7, 8]:  # Лето — пик
                seasonal_mult = 1.4
                season_label = "Высокий сезон (лето)"
            elif month in [5, 9]:  # Май/Сентябрь
                seasonal_mult = 1.1
                season_label = "Средний сезон"
            elif month in [12, 1, 2]:  # Зима
                seasonal_mult = 0.7
                season_label = "Низкий сезон (зима)"
        
        # === 3. Demand (конкуренция) ===
        if competitors_count < 3:
            demand_mult = 1.15  # Мало конкурентов → можно поднять
            demand_label = "Мало конкурентов"
        elif competitors_count > 15:
            demand_mult = 0.9   # Много конкурентов → скидка
            demand_label = "Высокая конкуренция"
        else:
            demand_mult = 1.0
            demand_label = "Средняя конкуренция"
        
        # === Итог ===
        total_mult = score_mult * seasonal_mult * demand_mult
        final_price = base_price * total_mult
        
        return PricingResult(
            base_price=base_price,
            final_price=final_price,
            multiplier=total_mult,
            factors={
                "tourosat_score": {
                    "score": round(tourosat_score, 1),
                    "multiplier": score_mult,
                    "label": score_label,
                },
                "seasonal": {
                    "multiplier": seasonal_mult,
                    "label": season_label,
                },
                "demand": {
                    "multiplier": demand_mult,
                    "label": demand_label,
                },
            },
        )