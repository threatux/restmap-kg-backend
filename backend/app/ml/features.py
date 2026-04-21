"""
TOUROSAT v3 — 24 спутниковых признака для оценки локации
"""
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class TourismFeatures:
    """
    24 параметра для оценки потенциала локации.
    Используется как input для ensemble моделей.
    """
    
    # === 🛰 Satellite Vegetation (Sentinel-2) ===
    ndvi: float                         # Индекс растительности (-1 to 1)
    ndwi: float                         # Индекс воды (-1 to 1)
    evi: float                          # Enhanced Vegetation Index
    savi: float                         # Soil-Adjusted Vegetation Index
    
    # === 🏔 Terrain (SRTM DEM) ===
    elevation_m: float                  # Высота над уровнем моря
    slope_degrees: float                # Крутизна склона
    aspect_degrees: float               # Ориентация склона (0-360)
    terrain_ruggedness: float          # Рельеф (0-1)
    
    # === 💧 Water & Climate ===
    distance_to_water_m: float         # Расстояние до воды
    water_body_area_km2: float         # Площадь ближайшего водоёма
    avg_temperature_c: float            # Средняя температура
    precipitation_mm: float             # Осадки
    sunshine_hours: float               # Часы солнца в день
    
    # === 🌱 Landscape Quality ===
    landscape_diversity: float          # Разнообразие ландшафта (0-1)
    forest_cover_pct: float             # % лесного покрова
    green_space_score: float            # 0-1
    
    # === 🏨 Competition & Infrastructure (OSM) ===
    competitors_count: int              # Отелей/юрт в радиусе 5км
    avg_competitor_rating: float        # Средний рейтинг конкурентов
    distance_to_road_m: float          # До дороги
    road_quality: float                 # 0-1
    
    # === 📈 Demand Indicators ===
    search_trend_score: float           # 0-1 (Google Trends proxy)
    seasonality_index: float            # 0-1
    accessibility_score: float          # 0-1 (Бишкек → точка)
    
    # === 🎯 Unique Factor ===
    uniqueness_score: float             # 0-1 (насколько редкая локация)
    
    def to_array(self) -> List[float]:
        """Конвертация в массив для нейросети"""
        return [
            self.ndvi, self.ndwi, self.evi, self.savi,
            self.elevation_m, self.slope_degrees, self.aspect_degrees, self.terrain_ruggedness,
            self.distance_to_water_m, self.water_body_area_km2, self.avg_temperature_c, 
            self.precipitation_mm, self.sunshine_hours,
            self.landscape_diversity, self.forest_cover_pct, self.green_space_score,
            float(self.competitors_count), self.avg_competitor_rating, self.distance_to_road_m, self.road_quality,
            self.search_trend_score, self.seasonality_index, self.accessibility_score,
            self.uniqueness_score,
        ]
    
    def to_dict(self) -> Dict:
        """Для сохранения в БД (JSON)"""
        return {
            "vegetation": {
                "ndvi": round(self.ndvi, 3),
                "ndwi": round(self.ndwi, 3),
                "evi": round(self.evi, 3),
                "savi": round(self.savi, 3),
            },
            "terrain": {
                "elevation_m": round(self.elevation_m, 1),
                "slope_degrees": round(self.slope_degrees, 2),
                "aspect_degrees": round(self.aspect_degrees, 1),
                "ruggedness": round(self.terrain_ruggedness, 3),
            },
            "climate": {
                "distance_to_water_m": round(self.distance_to_water_m, 1),
                "water_body_area_km2": round(self.water_body_area_km2, 2),
                "avg_temperature_c": round(self.avg_temperature_c, 1),
                "precipitation_mm": round(self.precipitation_mm, 1),
                "sunshine_hours": round(self.sunshine_hours, 1),
            },
            "landscape": {
                "diversity": round(self.landscape_diversity, 3),
                "forest_cover_pct": round(self.forest_cover_pct, 1),
                "green_score": round(self.green_space_score, 3),
            },
            "competition": {
                "competitors_count": self.competitors_count,
                "avg_competitor_rating": round(self.avg_competitor_rating, 2),
                "distance_to_road_m": round(self.distance_to_road_m, 1),
                "road_quality": round(self.road_quality, 2),
            },
            "demand": {
                "search_trend_score": round(self.search_trend_score, 3),
                "seasonality_index": round(self.seasonality_index, 3),
                "accessibility_score": round(self.accessibility_score, 3),
            },
            "uniqueness": round(self.uniqueness_score, 3),
        }


# === Названия параметров для UI ===
FEATURE_NAMES_RU = [
    "NDVI (растительность)",
    "NDWI (вода)",
    "EVI (улучшенная растительность)",
    "SAVI (почва)",
    "Высота над уровнем моря",
    "Крутизна склона",
    "Ориентация склона",
    "Рельеф местности",
    "Расстояние до воды",
    "Площадь водоёма",
    "Средняя температура",
    "Осадки",
    "Часы солнца",
    "Разнообразие ландшафта",
    "% лесного покрова",
    "Зелёная зона",
    "Количество конкурентов",
    "Рейтинг конкурентов",
    "Расстояние до дороги",
    "Качество дороги",
    "Тренд поисковых запросов",
    "Сезонность",
    "Доступность из Бишкека",
    "Уникальность локации",
]

FEATURE_NAMES_EN = [
    "NDVI (vegetation)",
    "NDWI (water)",
    "EVI (enhanced vegetation)",
    "SAVI (soil adjusted)",
    "Elevation (m)",
    "Slope (degrees)",
    "Aspect (degrees)",
    "Terrain ruggedness",
    "Distance to water",
    "Water body area",
    "Avg temperature",
    "Precipitation",
    "Sunshine hours",
    "Landscape diversity",
    "Forest cover %",
    "Green space score",
    "Competitors count",
    "Avg competitor rating",
    "Distance to road",
    "Road quality",
    "Search trend",
    "Seasonality",
    "Accessibility",
    "Uniqueness",
]