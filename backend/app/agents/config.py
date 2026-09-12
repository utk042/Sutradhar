"""Loads pipeline.yaml.

Kept separate from the graph so the configuration can be read and validated
without building anything, and so a malformed file fails at startup with a clear
message rather than halfway through an officer's upload.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

PIPELINE_PATH = Path(__file__).resolve().parents[1] / "pipeline.yaml"


class CheckConfig(BaseModel):
    name: str
    enabled: bool = True
    stage: str = "specialist"
    reads: str | None = None
    label_key: str
    prompt: str


class PipelineConfig(BaseModel):
    version: int
    checks: list[CheckConfig]
    severity: dict[str, str] = Field(default_factory=dict)

    @property
    def enabled_checks(self) -> list[CheckConfig]:
        return [c for c in self.checks if c.enabled]

    def severity_for(self, key: str, fallback: str) -> str:
        return self.severity.get(key, fallback)


@lru_cache
def load_pipeline() -> PipelineConfig:
    with PIPELINE_PATH.open(encoding="utf-8") as handle:
        return PipelineConfig.model_validate(yaml.safe_load(handle))
