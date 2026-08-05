"""
Configuration management for the Linear Regression model.

This module provides centralized configuration for reproducibility,
feature selection, and hyperparameter management.

Author: ML Engineering Team
Date: 2025-01-16
"""

from dataclasses import dataclass
from typing import List, Optional
import yaml
import os


@dataclass
class LinearRegressionConfig:
    """
    Configuration for the Linear Regression pipeline.
    
    Attributes:
        random_seed (int): Random seed for reproducibility across train/test split
        test_size (float): Fraction of data to use for testing (0.0-1.0)
        shuffle (bool): Whether to shuffle before splitting (False maintains temporal order)
        normalize_features (bool): Whether to standardize features (zero mean, unit variance)
        feature_selection_mode (str): 'all' for all cities, 'specific' for selected cities
        selected_cities (Optional[List[str]]): Cities to include if using specific mode
        target_column (str): Name of the target variable column
        date_column (str): Name of the date/datetime column
        city_column (str): Name of the city column
        temporal_features (List[str]): Temporal features to create
    """
    
    # Random seed for reproducibility
    random_seed: int = 42
    
    # Train/test split parameters
    test_size: float = 0.2  # 80/20 split
    shuffle: bool = False   # Maintain temporal order for time series
    
    # Feature scaling
    normalize_features: bool = True
    
    # Feature selection
    feature_selection_mode: str = "all"  # 'all' or 'specific'
    selected_cities: Optional[List[str]] = None
    
    # Column names
    target_column: str = "Temperature_C"
    date_column: str = "Date_Time"
    city_column: str = "City"
    
    # Features to generate from datetime
    temporal_features: List[str] = None
    
    def __post_init__(self) -> None:
        """Initialize default temporal features if not provided."""
        if self.temporal_features is None:
            self.temporal_features = ["day_of_year", "month", "year", "day_of_week"]
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "LinearRegressionConfig":
        """
        Load configuration from YAML file.
        
        Args:
            yaml_path (str): Path to YAML configuration file
            
        Returns:
            LinearRegressionConfig: Configuration object
            
        Raises:
            FileNotFoundError: If YAML file does not exist
            yaml.YAMLError: If YAML is malformed
        """
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
        
        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Extract only the keys that LinearRegressionConfig accepts
        valid_keys = {
            'random_seed', 'test_size', 'shuffle', 'normalize_features',
            'feature_selection_mode', 'selected_cities', 'target_column',
            'date_column', 'city_column', 'temporal_features'
        }
        
        filtered_config = {k: v for k, v in config_dict.items() if k in valid_keys}
        return cls(**filtered_config)
    
    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.
        
        Returns:
            dict: Configuration as dictionary
        """
        return {
            'random_seed': self.random_seed,
            'test_size': self.test_size,
            'shuffle': self.shuffle,
            'normalize_features': self.normalize_features,
            'feature_selection_mode': self.feature_selection_mode,
            'selected_cities': self.selected_cities,
            'target_column': self.target_column,
            'date_column': self.date_column,
            'city_column': self.city_column,
            'temporal_features': self.temporal_features,
        }


# Default configuration instance
DEFAULT_CONFIG = LinearRegressionConfig()
