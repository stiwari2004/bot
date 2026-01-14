"""
Incident prediction services
"""
# Import with error handling to prevent startup failures
try:
    from app.services.prediction.log_ingestion_service import LogIngestionService
except ImportError as e:
    LogIngestionService = None

try:
    from app.services.prediction.log_normalizer import LogNormalizer
except ImportError as e:
    LogNormalizer = None

try:
    from app.services.prediction.log_pattern_extractor import LogPatternExtractor
except ImportError as e:
    LogPatternExtractor = None

try:
    from app.services.prediction.prediction_aggregator import PredictionAggregator
except ImportError as e:
    PredictionAggregator = None

try:
    from app.services.prediction.feature_engineering import FeatureEngineeringService
except ImportError as e:
    FeatureEngineeringService = None

try:
    from app.services.prediction.historical_analyzer import HistoricalAnalyzer
except ImportError as e:
    HistoricalAnalyzer = None

try:
    from app.services.prediction.short_term_predictor import ShortTermPredictor
except ImportError as e:
    ShortTermPredictor = None

try:
    from app.services.prediction.medium_term_predictor import MediumTermPredictor
except ImportError as e:
    MediumTermPredictor = None

try:
    from app.services.prediction.long_term_predictor import LongTermPredictor
except ImportError as e:
    LongTermPredictor = None

try:
    from app.services.prediction.model_training_service import ModelTrainingService
except ImportError as e:
    ModelTrainingService = None

__all__ = [
    "LogIngestionService",
    "LogNormalizer",
    "LogPatternExtractor",
    "PredictionAggregator",
    "FeatureEngineeringService",
    "HistoricalAnalyzer",
    "ShortTermPredictor",
    "MediumTermPredictor",
    "LongTermPredictor",
    "ModelTrainingService",
]

