from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

_BPR_ALPHA = 0.15
_BPR_BETA  = 4.0
_FREE_FLOW_SPEED = 38.0   # km/h for existing roads

_PERIOD_MAP = {
    'Morning_Peak(veh/h)': 'morning',
    'Afternoon(veh/h)':    'afternoon',
    'Evening_Peak(veh/h)': 'evening',
    'Night(veh/h)':        'night',
}

# Feature column names used by the pipeline
NUMERIC_FEATURES     = ['distance_km', 'capacity', 'condition', 'traffic_volume']
CATEGORICAL_FEATURES = ['time_of_day']
ALL_FEATURES         = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Default output path (relative to project root)
MODEL_DIR  = Path(__file__).resolve().parent / 'models'
MODEL_PATH = MODEL_DIR / 'traffic_gb_model.pkl'

def _compute_bpr_target(row: pd.Series) -> float:
    d    = row['distance_km']
    cap  = row['capacity']
    cond = row['condition']
    vol  = row['traffic_volume']

    ratio      = max(0.0, vol / cap) if cap > 0 else 0.0
    bpr_factor = 1.0 + _BPR_ALPHA * (ratio ** _BPR_BETA)
    cond_factor = 1.0 + max(0.0, 7.0 - cond) * 0.02
    return (d / _FREE_FLOW_SPEED) * bpr_factor * cond_factor

def build_training_data(data_dir: Path) -> pd.DataFrame:
    roads_df = pd.read_csv(data_dir / 'Existing_Roads.csv')
    traffic_df = pd.read_csv(data_dir / 'Traffic_Flow.csv')

    # Normalize road IDs for join
    roads_df['road_id'] = (
        roads_df['FromID'].astype(str).str.strip()
        + '-'
        + roads_df['ToID'].astype(str).str.strip()
    )

    # Melt traffic flow from wide to long format
    traffic_long = traffic_df.melt(
        id_vars=['RoadID'],
        value_vars=list(_PERIOD_MAP.keys()),
        var_name='period_col',
        value_name='traffic_volume',
    )
    traffic_long['time_of_day'] = traffic_long['period_col'].map(_PERIOD_MAP)
    traffic_long['road_id'] = traffic_long['RoadID'].astype(str).str.strip()

    # Join
    merged = roads_df.merge(traffic_long, on='road_id', how='inner')

    # Rename / select columns
    merged = merged.rename(columns={
        'Distance(km)':                     'distance_km',
        'Current_Capacity(vehicles/hour)':  'capacity',
        'Condition(1-10)':                  'condition',
    })

    # Compute BPR target
    merged['travel_time_h'] = merged.apply(_compute_bpr_target, axis=1)

    return merged[ALL_FEATURES + ['travel_time_h']]

def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), NUMERIC_FEATURES),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False),
             CATEGORICAL_FEATURES),
        ],
        remainder='drop',
    )

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', HistGradientBoostingRegressor(
            max_iter=200,
            max_depth=5,
            learning_rate=0.1,
            min_samples_leaf=4,
            random_state=42,
        )),
    ])
    return pipeline

def train_and_save(data_dir: Path, output_path: Path | None = None) -> Path:
    out = output_path or MODEL_PATH

    print(f"[ML] Loading training data from {data_dir} ...")
    df = build_training_data(data_dir)
    print(f"[ML] Training samples: {len(df)} ({df['time_of_day'].nunique()} periods × "
          f"{len(df) // max(df['time_of_day'].nunique(), 1)} roads)")

    X = df[ALL_FEATURES]
    y = df['travel_time_h']

    print("[ML] Building pipeline: StandardScaler + OneHotEncoder → HistGradientBoostingRegressor")
    pipeline = build_pipeline()

    # Cross-validation for diagnostics
    scores = cross_val_score(pipeline, X, y, cv=min(5, len(df)), scoring='r2')
    print(f"[ML] Cross-validation R² scores: {scores.round(4)}")
    print(f"[ML] Mean R²: {scores.mean():.4f} ± {scores.std():.4f}")

    # Final fit on all data
    pipeline.fit(X, y)

    # Save
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, out)
    print(f"[ML] Pipeline saved to: {out}")
    print(f"[ML] Model size: {out.stat().st_size / 1024:.1f} KB")

    return out

def main():
    parser = argparse.ArgumentParser(description='Train the traffic prediction model')
    parser.add_argument('--data-dir', type=Path, default=Path('data'),
                        help='Path to the CSV data directory')
    parser.add_argument('--output', type=Path, default=None,
                        help='Output path for the .pkl model file')
    args = parser.parse_args()
    train_and_save(args.data_dir, args.output)

if __name__ == '__main__':
    main()
