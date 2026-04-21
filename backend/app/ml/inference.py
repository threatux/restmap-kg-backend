"""
TOUROSAT v3 — Ensemble inference
Предсказывает score для локации на основе 24 признаков.
"""
import torch
import numpy as np
import joblib
import json
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

from app.ml.model_architecture import (
    TourismScoreNetV3,
    TourismScoreNetDeep,
    TourismScoreNetWide,
)
from app.ml.features import TourismFeatures, FEATURE_NAMES_RU
from backend.app.core.config import settings


@dataclass
class TourosatResult:
    """Результат работы TOUROSAT"""
    score: float                    # 0-100
    confidence: float               # 0-1
    individual_scores: List[float]  # Scores от каждой модели
    features: Dict                  # 24 признака (для UI)
    insights: List[str]             # AI-сгенерированные инсайты
    top_factors: List[Dict]         # Топ-5 факторов, влияющих на score
    method: str = "ensemble_v3"
    
    def to_dict(self):
        return {
            "tourism_score": round(self.score, 1),
            "confidence": round(self.confidence, 3),
            "method": self.method,
            "individual_scores": [round(s, 1) for s in self.individual_scores],
            "features": self.features,
            "insights": self.insights,
            "top_factors": self.top_factors,
        }


class TourosatEngine:
    """
    Главный класс инференса TOUROSAT v3.
    Singleton — загружается 1 раз при старте FastAPI.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.models_dir = Path(settings.TOUROSAT_MODELS_DIR)
        
        self.model_v3 = None
        self.model_deep = None
        self.model_wide = None
        self.scaler = None
        self.metadata = None
        self.weights = [0.4, 0.35, 0.25]
        
        self._load_models()
        self._initialized = True
    
    def _load_models(self):
        """Загружает все 3 модели + scaler"""
        try:
            # Metadata
            metadata_path = self.models_dir / "ensemble_metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    self.metadata = json.load(f)
                    self.weights = self.metadata.get("weights", [0.4, 0.35, 0.25])
            
            # Scaler
            scaler_path = self.models_dir / "scaler.pkl"
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
            
            # Models
            self.model_v3 = TourismScoreNetV3().to(self.device)
            self.model_v3.load_state_dict(torch.load(self.models_dir / "model_v3.pth", map_location=self.device))
            self.model_v3.eval()
            
            self.model_deep = TourismScoreNetDeep().to(self.device)
            self.model_deep.load_state_dict(torch.load(self.models_dir / "model_deep.pth", map_location=self.device))
            self.model_deep.eval()
            
            self.model_wide = TourismScoreNetWide().to(self.device)
            self.model_wide = TourismScoreNetWide().to(self.device)
            self.model_wide.load_state_dict(torch.load(self.models_dir / "model_wide.pth", map_location=self.device))
            self.model_wide.eval()
            
            print(f"✅ TOUROSAT v3 loaded ({self.device})")
        except FileNotFoundError as e:
            print(f"⚠️  TOUROSAT models not found: {e}")
            print(f"    Run: python -m app.ml.train")
            self.model_v3 = None
    
    def is_ready(self) -> bool:
        return self.model_v3 is not None
    
    def predict(self, features: TourismFeatures) -> TourosatResult:
        """
        Главный метод — предсказывает score.
        
        Args:
            features: TourismFeatures (24 признака)
        
        Returns:
            TourosatResult со score + confidence + инсайтами
        """
        if not self.is_ready():
            # Fallback: экспертная формула
            return self._fallback_predict(features)
        
        # === Подготовка данных ===
        feature_array = np.array([features.to_array()], dtype=np.float32)
        if self.scaler is not None:
            feature_array = self.scaler.transform(feature_array).astype(np.float32)
        
        x = torch.tensor(feature_array, dtype=torch.float32).to(self.device)
        
        # === Ensemble predict ===
        with torch.no_grad():
            score_v3, confidence_v3 = self.model_v3(x)
            score_deep = self.model_deep(x)
            score_wide = self.model_wide(x)
            
            scores = [
                float(score_v3.item()),
                float(score_deep.item()),
                float(score_wide.item()),
            ]
            
            # Weighted average
            final_score = sum(s * w for s, w in zip(scores, self.weights))
            final_score = max(0.0, min(100.0, final_score))
            
            # Confidence:
            #   1. От модели #1 (она выдаёт)
            #   2. Дисперсия между моделями (меньше = выше confidence)
            std = float(np.std(scores))
            agreement_confidence = max(0.0, 1.0 - std / 20.0)
            final_confidence = (float(confidence_v3.item()) + agreement_confidence) / 2
        
        # === Insights + top factors ===
        insights = self._generate_insights(features, final_score)
        top_factors = self._analyze_top_factors(features)
        
        return TourosatResult(
            score=final_score,
            confidence=final_confidence,
            individual_scores=scores,
            features=features.to_dict(),
            insights=insights,
            top_factors=top_factors,
        )
    
    def _fallback_predict(self, features: TourismFeatures) -> TourosatResult:
        """Если модели не загружены — экспертная формула"""
        f = features
        score = (
            20 * max(f.ndvi, 0)
            + 15 * (1 - min(f.distance_to_water_m / 5000, 1))
            + 10 * (1 - min(f.competitors_count / 20, 1))
            + 10 * f.search_trend_score
            + 10 * f.uniqueness_score
            + 10 * f.accessibility_score
            + 5 * f.landscape_diversity
            + 5 * min(f.sunshine_hours / 12, 1)
            + 5 * (1 - min(f.slope_degrees / 45, 1))
            + 10 * (1 if 1600 < f.elevation_m < 2500 else 0.5)
        )
        score = max(0, min(100, score))
        
        return TourosatResult(
            score=score,
            confidence=0.5,
            individual_scores=[score, score, score],
            features=f.to_dict(),
            insights=self._generate_insights(f, score),
            top_factors=self._analyze_top_factors(f),
            method="fallback_expert",
        )
    
    def _generate_insights(self, f: TourismFeatures, score: float) -> List[str]:
        """Генерирует человекочитаемые инсайты"""
        insights = []
        
        # === Общая оценка ===
        if score >= 85:
            insights.append("🏆 Исключительная локация — топ 5% Иссык-Куля")
        elif score >= 70:
            insights.append("✨ Сильная локация с высоким потенциалом")
        elif score >= 55:
            insights.append("👍 Хорошая локация, рекомендуется")
        elif score >= 40:
            insights.append("⚠️ Средняя локация, нужны улучшения")
        else:
            insights.append("❌ Сложная локация для туризма")
        
        # === Вода ===
        if f.distance_to_water_m < 500:
            insights.append(f"🌊 В {int(f.distance_to_water_m)}м от воды — огромное преимущество")
        elif f.distance_to_water_m < 2000:
            insights.append(f"💧 Близко к воде ({int(f.distance_to_water_m)}м)")
        
        # === Конкуренция ===
        if f.competitors_count < 3:
            insights.append(f"🎯 Мало конкурентов ({f.competitors_count}) — рынок свободен")
        elif f.competitors_count > 15:
            insights.append(f"⚔️ Высокая конкуренция ({f.competitors_count} точек рядом)")
        
        # === Природа ===
        if f.ndvi > 0.6:
            insights.append("🌿 Богатая растительность — эко-туризм")
        if f.forest_cover_pct > 40:
            insights.append(f"🌲 Лесной покров {f.forest_cover_pct:.0f}% — приватность")
        
        # === Доступность ===
        if f.accessibility_score > 0.7:
            insights.append("🚗 Лёгкая доступность из Бишкека")
        elif f.accessibility_score < 0.3:
            insights.append("🏔 Удалённая локация — нужен трансфер")
        
        # === Уникальность ===
        if f.uniqueness_score > 0.7:
            insights.append("💎 Скрытая жемчужина — уникальная локация")
        
        # === Тренд спроса ===
        if f.search_trend_score > 0.7:
            insights.append("📈 Высокий тренд спроса в соцсетях")
        
        # === Высота ===
        if 1800 < f.elevation_m < 2200:
            insights.append(f"⛰ Оптимальная высота {int(f.elevation_m)}м")
        elif f.elevation_m > 2800:
            insights.append(f"🏔 Высокогорье ({int(f.elevation_m)}м) — только летом")
        
        return insights[:6]  # Максимум 6 инсайтов
    
    def _analyze_top_factors(self, f: TourismFeatures) -> List[Dict]:
        """
        Топ-5 факторов, которые больше всего влияют на score.
        Для красивой визуализации на фронте.
        """
        factors = [
            {
                "name": "Близость к воде",
                "value": round(1 - min(f.distance_to_water_m / 5000, 1), 2),
                "impact": "positive" if f.distance_to_water_m < 2000 else "neutral",
                "display": f"{int(f.distance_to_water_m)}м до воды",
            },
            {
                "name": "Конкуренция",
                "value": round(1 - min(f.competitors_count / 20, 1), 2),
                "impact": "positive" if f.competitors_count < 5 else "negative",
                "display": f"{f.competitors_count} конкурентов в 5км",
            },
            {
                "name": "Тренд спроса",
                "value": round(f.search_trend_score, 2),
                "impact": "positive" if f.search_trend_score > 0.5 else "neutral",
                "display": f"{int(f.search_trend_score * 100)}% спрос",
            },
            {
                "name": "Растительность (NDVI)",
                "value": round(max(f.ndvi, 0), 2),
                "impact": "positive" if f.ndvi > 0.4 else "neutral",
                "display": f"NDVI {f.ndvi:.2f}",
            },
            {
                "name": "Уникальность",
                "value": round(f.uniqueness_score, 2),
                "impact": "positive" if f.uniqueness_score > 0.5 else "neutral",
                "display": f"{int(f.uniqueness_score * 100)}% уникальность",
            },
            {
                "name": "Доступность",
                "value": round(f.accessibility_score, 2),
                "impact": "positive" if f.accessibility_score > 0.5 else "negative",
                "display": f"{int(f.accessibility_score * 100)}% доступность",
            },
        ]
        # Сортируем по value
        factors.sort(key=lambda x: x["value"], reverse=True)
        return factors[:5]


# === Singleton ===
tourosat_engine = TourosatEngine()


# === Helper Function ===
def extract_features_from_coords(lat: float, lon: float, 
                                   user_data: dict = None) -> TourismFeatures:
    """
    Извлекает 24 признака для координат.
    В реальности — из Sentinel-2 / Google Earth Engine.
    Сейчас — реалистичная симуляция для Иссык-Куля.
    """
    import hashlib
    
    # Seed по координатам — чтобы одна точка всегда давала одинаковые признаки
    seed = int(hashlib.md5(f"{lat:.4f}_{lon:.4f}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)
    
    # === Иссык-Куль: геопривязка ===
    # Центр озера: ~42.45, 77.15
    # Расстояние до центра озера (км)
    lake_center_lat, lake_center_lon = 42.45, 77.15
    dist_to_lake_center = np.sqrt((lat - lake_center_lat)**2 + (lon - lake_center_lon)**2) * 111
    
    # Если точка рядом с озером — distance_to_water мал
    if dist_to_lake_center < 60:  # В пределах 60км от центра
        dist_water = max(50, (dist_to_lake_center - 30) * 1000 + rng.uniform(100, 1500))
    else:
        dist_water = rng.uniform(2000, 15000)
    
    # Высота: в Иссык-Куле 1600-4000
    elevation = 1600 + rng.uniform(0, 600) + dist_to_lake_center * 20
    elevation = min(elevation, 4000)
    
    # NDVI — зависит от региона (южный берег зеленее)
    is_south = lat < 42.4
    ndvi = rng.uniform(0.3, 0.75) if is_south else rng.uniform(0.1, 0.5)
    
    # Override по user_data (если передали)
    user_data = user_data or {}
    
    return TourismFeatures(
        ndvi=user_data.get("ndvi", ndvi),
        ndwi=user_data.get("ndwi", rng.uniform(-0.1, 0.4)),
        evi=rng.uniform(0.2, 0.7),
        savi=rng.uniform(0.2, 0.6),
        elevation_m=user_data.get("elevation_m", elevation),
        slope_degrees=rng.uniform(2, 25),
        aspect_degrees=rng.uniform(0, 360),
        terrain_ruggedness=rng.uniform(0.1, 0.6),
        distance_to_water_m=user_data.get("distance_to_water_m", dist_water),
        water_body_area_km2=6236 if dist_water < 2000 else rng.uniform(0.5, 50),
        avg_temperature_c=rng.uniform(8, 18),
        precipitation_mm=rng.uniform(15, 80),
        sunshine_hours=rng.uniform(6, 10),
        landscape_diversity=rng.uniform(0.4, 0.9),
        forest_cover_pct=rng.uniform(5, 60),
        green_space_score=rng.uniform(0.3, 0.8),
        competitors_count=user_data.get("competitors_count", rng.randint(0, 15)),
        avg_competitor_rating=rng.uniform(3.2, 4.7),
        distance_to_road_m=rng.uniform(50, 2000),
        road_quality=rng.uniform(0.4, 0.9),
        search_trend_score=user_data.get("search_trend_score", rng.uniform(0.2, 0.9)),
        seasonality_index=rng.uniform(0.3, 0.9),
        accessibility_score=user_data.get("accessibility_score", rng.uniform(0.3, 0.9)),
        uniqueness_score=user_data.get("uniqueness_score", rng.uniform(0.2, 0.9)),
    )