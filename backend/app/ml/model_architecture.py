"""
TOUROSAT v3 — Architecture of neural networks
Ensemble из 3 моделей:
  1. TourismScoreNetV3 — основная (attention + residual)
  2. TourismScoreNetDeep — глубокая для сложных паттернов
  3. TourismScoreNetWide — широкая для простых линейных зависимостей
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class AttentionBlock(nn.Module):
    """Self-attention для 24 признаков"""
    def __init__(self, dim: int):
        super().__init__()
        self.query = nn.Linear(dim, dim)
        self.key = nn.Linear(dim, dim)
        self.value = nn.Linear(dim, dim)
        self.scale = dim ** 0.5
    
    def forward(self, x):
        q = self.query(x)
        k = self.key(x)
        v = self.value(x)
        attn = F.softmax(q @ k.transpose(-2, -1) / self.scale, dim=-1)
        return attn @ v


class ResidualBlock(nn.Module):
    """Residual connection для стабильного обучения"""
    def __init__(self, dim: int, dropout: float = 0.2):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim * 2)
        self.fc2 = nn.Linear(dim * 2, dim)
        self.norm = nn.LayerNorm(dim)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        residual = x
        x = F.gelu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return self.norm(x + residual)


class TourismScoreNetV3(nn.Module):
    """
    Модель #1: Основная с attention + residual.
    Вход: 24 признака.
    Выход: score (0-100) + confidence (0-1).
    """
    def __init__(self, n_features: int = 24, hidden_dim: int = 128):
        super().__init__()
        self.input_proj = nn.Linear(n_features, hidden_dim)
        self.attention = AttentionBlock(hidden_dim)
        self.residual1 = ResidualBlock(hidden_dim)
        self.residual2 = ResidualBlock(hidden_dim)
        self.residual3 = ResidualBlock(hidden_dim)
        
        # Два выхода: score и confidence
        self.score_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
            nn.Sigmoid(),  # 0-1 → потом *100
        )
        
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )
    
    def forward(self, x):
        x = self.input_proj(x)
        x = self.attention(x.unsqueeze(1)).squeeze(1)
        x = self.residual1(x)
        x = self.residual2(x)
        x = self.residual3(x)
        
        score = self.score_head(x) * 100  # 0-100
        confidence = self.confidence_head(x)
        return score, confidence


class TourismScoreNetDeep(nn.Module):
    """
    Модель #2: Глубокая — для сложных паттернов.
    """
    def __init__(self, n_features: int = 24):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 256),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(256, 512),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.GELU(),
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )
    
    def forward(self, x):
        return self.net(x) * 100


class TourismScoreNetWide(nn.Module):
    """
    Модель #3: Широкая — для простых линейных зависимостей.
    """
    def __init__(self, n_features: int = 24):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 1024),
            nn.GELU(),
            nn.Dropout(0.4),
            nn.Linear(1024, 256),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )
    
    def forward(self, x):
        return self.net(x) * 100