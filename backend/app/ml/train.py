"""
TOUROSAT v3 — Обучение ensemble с нуля.
Генерируется синтетический датасет Иссык-Куля (50k samples).
"""
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import numpy as np
import joblib
from pathlib import Path
from sklearn.preprocessing import StandardScaler

from app.ml.model_architecture import (
    TourismScoreNetV3,
    TourismScoreNetDeep,
    TourismScoreNetWide,
)
from backend.app.core.config import settings


# ============ SYNTHETIC DATASET GENERATOR ============

class IssykKulSyntheticDataset(Dataset):
    """
    Синтетический датасет Иссык-Куля.
    Генерирует реалистичные 24 признака + ground truth score.
    
    Ground truth формула (экспертная оценка):
      score = 
        + 20 * max(ndvi, 0)              # Больше растительность — лучше
        + 15 * (1 - min(dist_water/5000, 1))  # Ближе к воде — лучше
        + 10 * (1 - competitors/20)      # Меньше конкурентов — лучше
        + 10 * search_trend              # Больше трендов — лучше
        + 10 * uniqueness                 # Уникальность
        + 10 * accessibility              # Доступность
        + 5 * landscape_diversity         # Разнообразие
        + 5 * sunshine_factor             # Солнечность
        + 5 * (1 - slope/45)              # Не слишком крутой
        + 10 * (elevation/3000 if 1600<elev<2500 else 0)  # Оптимальная высота
        + noise ~ N(0, 5)
    """
    
    def __init__(self, n_samples: int = 50000, seed: int = 42):
        np.random.seed(seed)
        self.n_samples = n_samples
        self.features, self.scores = self._generate()
    
    def _generate(self):
        n = self.n_samples
        
        # === Генерация признаков с реалистичными распределениями ===
        
        # Vegetation (NDVI, NDWI, EVI, SAVI) — в Иссык-Куле смешанно
        ndvi = np.random.beta(3, 4, n) * 1.2 - 0.2  # -0.2 до 1.0
        ndwi = np.random.beta(2, 5, n) * 1.2 - 0.2
        evi = ndvi + np.random.normal(0, 0.05, n)
        savi = ndvi * 0.8 + np.random.normal(0, 0.05, n)
        
        # Terrain (Иссык-Куль: 1600-4000м)
        elevation = np.random.normal(1900, 400, n).clip(1600, 4200)
        slope = np.random.exponential(10, n).clip(0, 70)
        aspect = np.random.uniform(0, 360, n)
        ruggedness = np.random.beta(2, 5, n)
        
        # Water (озеро рядом → многие точки близко)
        dist_water = np.random.exponential(2000, n).clip(10, 20000)
        water_area = np.random.exponential(500, n).clip(0.1, 6236)  # Иссык-Куль = 6236 км²
        
        # Climate (Иссык-Куль: умеренный)
        temp = np.random.normal(12, 6, n).clip(-15, 28)
        precipitation = np.random.exponential(30, n).clip(0, 200)
        sunshine = np.random.normal(8, 2, n).clip(2, 14)
        
        # Landscape
        landscape_div = np.random.beta(3, 3, n)
        forest_cover = np.random.beta(2, 5, n) * 100
        green_score = (landscape_div + forest_cover/100) / 2
        
        # Competition (в популярных местах — больше)
        competitors = np.random.poisson(5, n).clip(0, 30)
        comp_rating = np.random.normal(3.8, 0.6, n).clip(1, 5)
        
        # Roads
        dist_road = np.random.exponential(500, n).clip(10, 5000)
        road_quality = np.random.beta(3, 3, n)
        
        # Demand
        search_trend = np.random.beta(2, 5, n)
        seasonality = np.random.beta(3, 3, n)
        accessibility = np.random.beta(3, 3, n)
        
        # Uniqueness
        uniqueness = np.random.beta(2, 5, n)
        
        # === Собираем в матрицу ===
        features = np.column_stack([
            ndvi, ndwi, evi, savi,
            elevation, slope, aspect, ruggedness,
            dist_water, water_area, temp, precipitation, sunshine,
            landscape_div, forest_cover, green_score,
            competitors, comp_rating, dist_road, road_quality,
            search_trend, seasonality, accessibility,
            uniqueness,
        ])
        
        # === Ground Truth Score (экспертная формула) ===
        scores = (
            20 * np.clip(ndvi, 0, 1)
            + 15 * (1 - np.clip(dist_water / 5000, 0, 1))
            + 10 * (1 - np.clip(competitors / 20, 0, 1))
            + 10 * search_trend
            + 10 * uniqueness
            + 10 * accessibility
            + 5 * landscape_div
            + 5 * np.clip(sunshine / 12, 0, 1)
            + 5 * (1 - np.clip(slope / 45, 0, 1))
            + 10 * np.where(
                (elevation > 1600) & (elevation < 2500),
                (elevation - 1600) / 900,
                np.maximum(0, 1 - np.abs(elevation - 2000) / 2000)
            )
            + np.random.normal(0, 3, n)  # Шум
        ).clip(0, 100)
        
        return features.astype(np.float32), scores.astype(np.float32)
    
    def __len__(self):
        return self.n_samples
    
    def __getitem__(self, idx):
        return (
            torch.tensor(self.features[idx], dtype=torch.float32),
            torch.tensor(self.scores[idx], dtype=torch.float32),
        )


# ============ TRAINING FUNCTION ============

def train_model(model, train_loader, val_loader, epochs: int = 30, lr: float = 1e-3, device: str = "cpu"):
    """Обучает одну модель"""
    model = model.to(device)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.HuberLoss(delta=5.0)
    
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        # === Training ===
        model.train()
        train_loss = 0.0
        for features, targets in train_loader:
            features, targets = features.to(device), targets.to(device)
            
            optimizer.zero_grad()
            output = model(features)
            
            # Если модель возвращает tuple (score, confidence)
            if isinstance(output, tuple):
                pred_score = output[0].squeeze()
            else:
                pred_score = output.squeeze()
            
            loss = criterion(pred_score, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()
        
        # === Validation ===
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for features, targets in val_loader:
                features, targets = features.to(device), targets.to(device)
                output = model(features)
                if isinstance(output, tuple):
                    pred_score = output[0].squeeze()
                else:
                    pred_score = output.squeeze()
                val_loss += criterion(pred_score, targets).item()
        
        scheduler.step()
        avg_train = train_loss / len(train_loader)
        avg_val = val_loss / len(val_loader)
        
        if avg_val < best_val_loss:
            best_val_loss = avg_val
        
        print(f"  Epoch {epoch+1}/{epochs} | Train: {avg_train:.3f} | Val: {avg_val:.3f}")
    
    return model, best_val_loss


def train_ensemble():
    """
    Обучает все 3 модели ensemble.
    Сохраняет веса в app/ml/models/
    """
    print("\n" + "=" * 60)
    print("🛰  TOUROSAT v3 — Training Ensemble")
    print("=" * 60 + "\n")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🖥  Device: {device}\n")
    
    # === Dataset ===
    print("📊 Generating synthetic Issyk-Kul dataset (50,000 samples)...")
    full_dataset = IssykKulSyntheticDataset(n_samples=50000)
    
    # Нормализация
    scaler = StandardScaler()
    scaler.fit(full_dataset.features)
    full_dataset.features = scaler.transform(full_dataset.features).astype(np.float32)
    
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_ds, val_ds = random_split(full_dataset, [train_size, val_size], generator=torch.Generator().manual_seed(42))
    
    train_loader = DataLoader(train_ds, batch_size=128, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=128, shuffle=False, num_workers=0)
    
    print(f"   Train: {train_size} | Val: {val_size}\n")
    
    # === Save Dir ===
    models_dir = Path(settings.TOUROSAT_MODELS_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Сохраняем scaler
    joblib.dump(scaler, models_dir / "scaler.pkl")
    print(f"💾 Saved scaler to {models_dir / 'scaler.pkl'}\n")
    
    # === Model 1: TourismScoreNetV3 ===
    print("🧠 Training Model 1/3: TourismScoreNetV3 (attention + residual)...")
    model1 = TourismScoreNetV3()
    model1, loss1 = train_model(model1, train_loader, val_loader, epochs=25, lr=1e-3, device=device)
    torch.save(model1.state_dict(), models_dir / "model_v3.pth")
    print(f"  ✅ Saved (val loss: {loss1:.3f})\n")
    
    # === Model 2: TourismScoreNetDeep ===
    print("🧠 Training Model 2/3: TourismScoreNetDeep...")
    model2 = TourismScoreNetDeep()
    model2, loss2 = train_model(model2, train_loader, val_loader, epochs=25, lr=1e-3, device=device)
    torch.save(model2.state_dict(), models_dir / "model_deep.pth")
    print(f"  ✅ Saved (val loss: {loss2:.3f})\n")
    
    # === Model 3: TourismScoreNetWide ===
    print("🧠 Training Model 3/3: TourismScoreNetWide...")
    model3 = TourismScoreNetWide()
    model3, loss3 = train_model(model3, train_loader, val_loader, epochs=25, lr=1e-3, device=device)
    torch.save(model3.state_dict(), models_dir / "model_wide.pth")
    print(f"  ✅ Saved (val loss: {loss3:.3f})\n")
    
    # === Ensemble Metadata ===
    metadata = {
        "version": "3.0",
        "n_features": 24,
        "ensemble_size": 3,
        "models": [
            {"name": "TourismScoreNetV3", "file": "model_v3.pth", "val_loss": round(loss1, 3)},
            {"name": "TourismScoreNetDeep", "file": "model_deep.pth", "val_loss": round(loss2, 3)},
            {"name": "TourismScoreNetWide", "file": "model_wide.pth", "val_loss": round(loss3, 3)},
        ],
        "weights": [0.4, 0.35, 0.25],  # V3 более важен
    }
    
    import json
    with open(models_dir / "ensemble_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print("=" * 60)
    print("✅ TOUROSAT v3 ensemble training COMPLETE")
    print(f"📁 Models saved to: {models_dir}")
    print("=" * 60)
    
    return metadata


if __name__ == "__main__":
    train_ensemble()