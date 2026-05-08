from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from src.models.entities import Edge

_log = logging.getLogger(__name__)

# Default path for the trained ML model
_ML_MODEL_PATH = Path(__file__).resolve().parent.parent / 'ml' / 'models' / 'traffic_gb_model.pkl'

# ---------------------------------------------------------------------------
# Optional ML dependencies — resolved at module import time so that the hot
# path (calculate) avoids repeated sys.modules dict lookups on every call.
# ---------------------------------------------------------------------------
try:
    import joblib
    import pandas as pd
    _ML_DEPS_AVAILABLE = True
except ImportError:
    _ML_DEPS_AVAILABLE = False


class WeightCalculationStrategy(ABC):

    @abstractmethod
    def calculate(self, edge: Edge, time_of_day: str, distance_km: float) -> float:
        ...


class BPRStrategy(WeightCalculationStrategy):

    def calculate(self, edge: Edge, time_of_day: str, distance_km: float) -> float:
        d = distance_km

        if edge.edge_type == 'existing_road':
            traffic = edge.traffic_flow.get(time_of_day)
            cap     = edge.capacity or 2500.0
            cond    = edge.condition or 7.0
            ratio   = max(0.0, (traffic or 0.0) / cap) if cap else 0.0
            # BPR travel-time model: T = T0 * (1 + alpha * (V/C)^beta).
            alpha, beta = 0.15, 4.0
            bpr_factor  = 1.0 + alpha * (ratio ** beta)
            cond_factor = 1.0 + max(0.0, 7.0 - cond) * 0.02
            return (d / 38.0) * bpr_factor * cond_factor

        elif edge.edge_type == 'potential_road':
            return d / 42.0

        elif edge.edge_type == 'bus':
            p, buses = edge.daily_passengers or 0.0, edge.buses_assigned
            return (d / 24.0) * (1.0 + min(1.2, p / 100000.0)) * (
                max(0.65, 1.15 - min(buses, 40) * 0.012) if buses else 1.0
            )

        elif edge.edge_type == 'metro':
            return (d / 45.0) * (1.0 + min(0.6, (edge.daily_passengers or 0.0) / 3000000.0))

        else:
            return d / 30.0


class MLPredictionStrategy(WeightCalculationStrategy):

    def __init__(
        self,
        model_path: Path | None = None,
        fallback: WeightCalculationStrategy | None = None,
    ):
        self._model_path = model_path or _ML_MODEL_PATH
        self._pipeline   = None
        # Fallback is injected — defaults to BPRStrategy for backward compatibility.
        self._fallback: WeightCalculationStrategy = fallback or BPRStrategy()
        self._load_model()

    def _load_model(self) -> None:
        if not _ML_DEPS_AVAILABLE:
            _log.warning(
                "joblib/pandas not installed — ML model unavailable, using BPR fallback."
            )
            return
        try:
            if self._model_path.exists():
                self._pipeline = joblib.load(self._model_path)
                _log.info("ML model loaded from %s", self._model_path)
            else:
                _log.warning(
                    "ML model not found at %s — using BPR fallback. "
                    "Run `python -m src.ml.train_traffic_model` to train.",
                    self._model_path,
                )
        except Exception as exc:
            _log.warning("Failed to load ML model: %s — using BPR fallback.", exc)
            self._pipeline = None

    def calculate(self, edge: Edge, time_of_day: str, distance_km: float) -> float:
        # ML prediction only applies to existing_road edges
        if edge.edge_type != 'existing_road' or self._pipeline is None:
            return self._fallback.calculate(edge, time_of_day, distance_km)

        try:
            features = pd.DataFrame([{
                'distance_km':    distance_km,
                'capacity':       edge.capacity or 2500.0,
                'condition':      edge.condition or 7.0,
                'traffic_volume': edge.traffic_flow.get(time_of_day, 0.0),
                'time_of_day':    time_of_day,
            }])
            prediction = self._pipeline.predict(features)[0]
            # Sanity guard: prediction must be positive and reasonable
            if prediction > 0 and prediction < 50.0:
                return float(prediction)
            _log.debug("ML prediction out of range (%.4f), using BPR fallback.", prediction)
        except Exception as exc:
            _log.debug("ML prediction failed: %s — using BPR fallback.", exc)

        return self._fallback.calculate(edge, time_of_day, distance_km)


_STRATEGY_REGISTRY: dict[str, type[WeightCalculationStrategy]] = {
    'bpr': BPRStrategy,
    'ml':  MLPredictionStrategy,
}


def _create_strategy(name: str) -> WeightCalculationStrategy:
    cls = _STRATEGY_REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown weight strategy '{name}'. "
            f"Available: {', '.join(_STRATEGY_REGISTRY.keys())}"
        )
    return cls()


class WeightEngine:

    VALID_TIME_OF_DAY = ('morning', 'afternoon', 'evening', 'night')
    TIME_OF_DAY_ALIASES = {
        'morning':      'morning',
        'morning peak': 'morning',
        'am peak':      'morning',
        'afternoon':    'afternoon',
        'evening':      'evening',
        'evening peak': 'evening',
        'pm peak':      'evening',
        'night':        'night',
    }

    def __init__(self, strategy: str = 'bpr'):
        # WeightEngine owns its own private cache 
        self._cache: dict[tuple, float] = {}
        self._strategy = _create_strategy(strategy)
        self._strategy_name = strategy

    @property
    def strategy_name(self) -> str:
        return self._strategy_name

    @classmethod
    def normalize_time_of_day(cls, time_of_day: str) -> str:
        key = ' '.join(
            str(time_of_day).strip().lower()
            .replace('_', ' ').replace('-', ' ').split()
        )
        t = cls.TIME_OF_DAY_ALIASES.get(key)
        if t is None:
            raise ValueError(
                f"Invalid time_of_day '{time_of_day}'. "
                f"Expected one of: {', '.join(cls.VALID_TIME_OF_DAY)}"
            )
        return t

    def get_edge_weight(self, edge: Edge, time_of_day: str = 'morning') -> float:
        t, d = self.normalize_time_of_day(time_of_day), edge.distance_km or 1.0
        cache_key = (
            edge.from_id, edge.to_id, edge.edge_type, t, d,
            edge.capacity, edge.condition, edge.construction_cost,
            edge.daily_passengers, edge.buses_assigned,
            edge.traffic_flow.get(t),
            self._strategy_name,  # different strategy → different cache entry
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        value = self._strategy.calculate(edge, t, d)

        self._cache[cache_key] = value
        return value
