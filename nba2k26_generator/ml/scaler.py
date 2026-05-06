"""Feature scaling utilities."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler


class AttributeScaler:
    """Scaler for NBA 2K26 attributes (0-100 range)."""
    
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(25, 95))
        self.fitted = False
    
    def fit(self, X: np.ndarray) -> "AttributeScaler":
        """Fit scaler to data."""
        self.scaler.fit(X)
        self.fitted = True
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform data."""
        if not self.fitted:
            raise ValueError("Scaler not fitted")
        return self.scaler.transform(X)
    
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fit and transform data."""
        self.fitted = True
        return self.scaler.fit_transform(X)
    
    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """Inverse transform scaled data back to original range."""
        if not self.fitted:
            raise ValueError("Scaler not fitted")
        return self.scaler.inverse_transform(X)
    
    def save(self, filepath: str):
        """Save scaler parameters."""
        import joblib
        joblib.dump(self.scaler, filepath)
    
    @classmethod
    def load(cls, filepath: str) -> "AttributeScaler":
        """Load scaler from file."""
        import joblib
        instance = cls()
        instance.scaler = joblib.load(filepath)
        instance.fitted = True
        return instance


class FeatureNormalizer:
    """Normalize raw features to standard range."""
    
    def __init__(self, method: str = "minmax"):
        self.method = method
        self.scalers: Dict[str, MinMaxScaler] = {}
        self.feature_names: List[str] = []
        self.fitted = False
    
    def fit(self, df: pd.DataFrame) -> "FeatureNormalizer":
        """Fit normalizer to dataframe."""
        self.feature_names = df.columns.tolist()
        
        for col in df.columns:
            data = df[col].values.reshape(-1, 1)
            
            if self.method == "minmax":
                scaler = MinMaxScaler()
            elif self.method == "standard":
                scaler = StandardScaler()
            elif self.method == "robust":
                scaler = RobustScaler()
            else:
                scaler = MinMaxScaler()
            
            try:
                scaler.fit(data)
                self.scalers[col] = scaler
            except Exception:
                pass
        
        self.fitted = True
        return self
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform dataframe."""
        if not self.fitted:
            raise ValueError("Normalizer not fitted")
        
        result = df.copy()
        
        for col in df.columns:
            if col in self.scalers:
                try:
                    data = df[col].values.reshape(-1, 1)
                    result[col] = self.scalers[col].transform(data)
                except Exception:
                    pass
        
        return result
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform."""
        self.fit(df)
        return self.transform(df)
    
    def inverse_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Inverse transform."""
        if not self.fitted:
            raise ValueError("Normalizer not fitted")
        
        result = df.copy()
        
        for col in df.columns:
            if col in self.scalers:
                try:
                    data = df[col].values.reshape(-1, 1)
                    result[col] = self.scalers[col].inverse_transform(data)
                except Exception:
                    pass
        
        return result
    
    def save(self, filepath: str):
        """Save normalizer."""
        import joblib
        joblib.dump({
            "scalers": self.scalers,
            "feature_names": self.feature_names,
            "method": self.method
        }, filepath)
    
    @classmethod
    def load(cls, filepath: str) -> "FeatureNormalizer":
        """Load normalizer from file."""
        import joblib
        data = joblib.load(filepath)
        instance = cls(method=data["method"])
        instance.scalers = data["scalers"]
        instance.feature_names = data["feature_names"]
        instance.fitted = True
        return instance


def normalize_percentages(df: pd.DataFrame, cols: List[str] = None) -> pd.DataFrame:
    """Normalize percentage columns (0-1 to 0-100)."""
    if cols is None:
        cols = [c for c in df.columns if "_PCT" in c.upper() or "_RATE" in c.upper()]
    
    result = df.copy()
    
    for col in cols:
        if col in df.columns:
            result[col] = df[col].apply(lambda x: x * 100 if pd.notna(x) and x <= 1 else x)
    
    return result


def clip_outliers(series: pd.Series, lower: float = None, upper: float = None) -> pd.Series:
    """Clip outliers to specified range."""
    if lower is None:
        lower = series.quantile(0.01)
    if upper is None:
        upper = series.quantile(0.99)
    
    return series.clip(lower, upper)


def handle_missing_values(df: pd.DataFrame, strategy: str = "median") -> pd.DataFrame:
    """Handle missing values in dataframe."""
    result = df.copy()
    
    for col in result.columns:
        if result[col].isna().any():
            if strategy == "median":
                result[col] = result[col].fillna(result[col].median())
            elif strategy == "mean":
                result[col] = result[col].fillna(result[col].mean())
            elif strategy == "zero":
                result[col] = result[col].fillna(0)
    
    return result


if __name__ == "__main__":
    print("Testing scaler utilities...")
    
    test_data = np.array([[0.4], [0.6], [0.8], [0.2], [0.5]])
    
    scaler = AttributeScaler()
    scaled = scaler.fit_transform(test_data)
    print(f"Scaled range: {scaled.min():.1f} - {scaled.max():.1f}")
    
    unscaled = scaler.inverse_transform(scaled)
    print(f"Unscaled matches: {np.allclose(test_data, unscaled)}")
