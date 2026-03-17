"""
Settings — benchmark config and infrastructure threshold endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.config_service import ConfigService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

_BENCHMARK_KEYS = [
    'confidence_threshold_existing',
    'confidence_threshold_duplicate',
    'min_runbook_success_rate',
]
_BENCHMARK_DEFAULTS = {
    'confidence_threshold_existing': ('0.75', 'Minimum similarity to suggest existing runbook'),
    'confidence_threshold_duplicate': ('0.80', 'Similarity threshold to flag as duplicate'),
    'min_runbook_success_rate': ('0.70', 'Minimum success rate for high-quality runbook'),
}
_INFRA_METRICS = ["cpu", "memory", "disk", "network"]
_INFRA_ENVS = ["prod", "staging", "dev"]
_INFRA_DEFAULTS = {
    "cpu":     {"prod": (70.0, 90.0), "staging": (80.0, 95.0), "dev": (90.0, 98.0)},
    "memory":  {"prod": (75.0, 90.0), "staging": (85.0, 95.0), "dev": (90.0, 98.0)},
    "disk":    {"prod": (80.0, 90.0), "staging": (85.0, 95.0), "dev": (90.0, 98.0)},
    "network": {"prod": (70.0, 85.0), "staging": (80.0, 90.0), "dev": (90.0, 95.0)},
}


class BenchmarkConfigItem(BaseModel):
    config_key: str
    config_value: str
    description: str


class BenchmarkConfigResponse(BaseModel):
    configs: list[BenchmarkConfigItem]


class UpdateBenchmarkConfigRequest(BaseModel):
    config_key: str
    config_value: str


class InfrastructureThresholdItem(BaseModel):
    metric: str
    environment: str
    warning_threshold: float
    critical_threshold: float


class InfrastructureThresholdResponse(BaseModel):
    thresholds: list[InfrastructureThresholdItem]


class UpdateInfrastructureThresholdRequest(BaseModel):
    metric: str
    environment: str
    warning_threshold: float = Field(ge=0.0, le=100.0)
    critical_threshold: float = Field(ge=0.0, le=100.0)


@router.get("/benchmark-config/demo", response_model=BenchmarkConfigResponse)
async def get_benchmark_config_demo(db: Session = Depends(get_db)):
    """Get benchmark configuration values (demo - no auth)"""
    try:
        from app.models.system_config import SystemConfig
        tenant_id = 1
        benchmark_configs = db.query(SystemConfig).filter(
            SystemConfig.tenant_id == tenant_id,
            SystemConfig.config_key.in_(_BENCHMARK_KEYS)
        ).all()

        items = [
            BenchmarkConfigItem(
                config_key=c.config_key,
                config_value=c.config_value,
                description=c.description or ""
            )
            for c in benchmark_configs
        ]
        existing_keys = {item.config_key for item in items}

        for key, (value, desc) in _BENCHMARK_DEFAULTS.items():
            if key not in existing_keys:
                ConfigService.set_config(db, tenant_id, key, value, desc)
                items.append(BenchmarkConfigItem(config_key=key, config_value=value, description=desc))

        return BenchmarkConfigResponse(configs=sorted(items, key=lambda x: x.config_key))
    except Exception as e:
        logger.error(f"Error getting benchmark config (demo): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get benchmark config: {str(e)}")


@router.post("/benchmark-config/demo", response_model=BenchmarkConfigResponse)
async def update_benchmark_config_demo(
    request: UpdateBenchmarkConfigRequest,
    db: Session = Depends(get_db)
):
    """Update benchmark configuration value (demo - no auth)"""
    try:
        if request.config_key not in _BENCHMARK_KEYS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid config_key. Must be one of: {', '.join(_BENCHMARK_KEYS)}"
            )
        try:
            value = float(request.config_value)
            if not (0.0 <= value <= 1.0):
                raise ValueError("Value must be between 0.0 and 1.0")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid config_value: {e}. Must be a number between 0.0 and 1.0")

        from app.models.system_config import SystemConfig
        existing = db.query(SystemConfig).filter(
            SystemConfig.tenant_id == 1,
            SystemConfig.config_key == request.config_key
        ).first()
        description = (existing.description if existing and existing.description
                       else _BENCHMARK_DEFAULTS.get(request.config_key, ("", ""))[1])

        ConfigService.set_config(db, 1, request.config_key, request.config_value, description)
        return await get_benchmark_config_demo(db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating benchmark config (demo): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update benchmark config: {str(e)}")


def _infra_config_key(metric: str, env: str, level: str) -> str:
    return f"infra_threshold_{metric}_{env}_{level}"


@router.get("/infrastructure-thresholds/demo", response_model=InfrastructureThresholdResponse)
async def get_infrastructure_thresholds_demo(db: Session = Depends(get_db)):
    """Get infrastructure threshold configuration (demo - no auth)"""
    try:
        from app.models.system_config import SystemConfig
        tenant_id = 1

        threshold_configs = db.query(SystemConfig).filter(
            SystemConfig.tenant_id == tenant_id,
            SystemConfig.config_key.like('infra_threshold_%')
        ).all()

        parsed: dict[str, dict] = {}
        for config in threshold_configs:
            parts = config.config_key.split('_')
            if len(parts) >= 5:
                metric, env, level = parts[2], parts[3], parts[4]
                key = f"{metric}_{env}"
                parsed.setdefault(key, {"metric": metric, "environment": env,
                                        "warning_threshold": None, "critical_threshold": None})
                try:
                    v = float(config.config_value)
                    if level == "warning":
                        parsed[key]["warning_threshold"] = v
                    elif level == "critical":
                        parsed[key]["critical_threshold"] = v
                except (ValueError, TypeError):
                    logger.warning(f"Invalid threshold value for {config.config_key}")

        items = []
        for metric in _INFRA_METRICS:
            for env in _INFRA_ENVS:
                key = f"{metric}_{env}"
                warn_def, crit_def = _INFRA_DEFAULTS[metric][env]
                row = parsed.get(key, {"metric": metric, "environment": env,
                                       "warning_threshold": None, "critical_threshold": None})
                if row["warning_threshold"] is None:
                    row["warning_threshold"] = warn_def
                    ConfigService.set_config(db, tenant_id, _infra_config_key(metric, env, "warning"),
                                             str(warn_def), f"{metric.upper()} warning threshold for {env}")
                if row["critical_threshold"] is None:
                    row["critical_threshold"] = crit_def
                    ConfigService.set_config(db, tenant_id, _infra_config_key(metric, env, "critical"),
                                             str(crit_def), f"{metric.upper()} critical threshold for {env}")
                items.append(InfrastructureThresholdItem(**row))

        return InfrastructureThresholdResponse(
            thresholds=sorted(items, key=lambda x: (x.metric, x.environment))
        )
    except Exception as e:
        logger.error(f"Error getting infrastructure thresholds (demo): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get infrastructure thresholds: {str(e)}")


@router.post("/infrastructure-thresholds/demo", response_model=InfrastructureThresholdResponse)
async def update_infrastructure_threshold_demo(
    request: UpdateInfrastructureThresholdRequest,
    db: Session = Depends(get_db)
):
    """Update infrastructure threshold configuration (demo - no auth)"""
    try:
        if request.metric not in _INFRA_METRICS:
            raise HTTPException(status_code=400, detail=f"Invalid metric. Must be one of: {', '.join(_INFRA_METRICS)}")
        if request.environment not in _INFRA_ENVS:
            raise HTTPException(status_code=400, detail=f"Invalid environment. Must be one of: {', '.join(_INFRA_ENVS)}")
        if request.warning_threshold >= request.critical_threshold:
            raise HTTPException(status_code=400, detail="Warning threshold must be less than critical threshold")

        ConfigService.set_config(
            db, 1, _infra_config_key(request.metric, request.environment, "warning"),
            str(request.warning_threshold),
            f"{request.metric.upper()} warning threshold for {request.environment} environment"
        )
        ConfigService.set_config(
            db, 1, _infra_config_key(request.metric, request.environment, "critical"),
            str(request.critical_threshold),
            f"{request.metric.upper()} critical threshold for {request.environment} environment"
        )
        return await get_infrastructure_thresholds_demo(db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating infrastructure threshold (demo): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update infrastructure threshold: {str(e)}")
