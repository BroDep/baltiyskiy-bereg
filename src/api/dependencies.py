from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

DependencyState = Literal["ready", "degraded"]
ProbeMode = Literal["ready", "error", "timeout", "malformed"]


@dataclass(slots=True)
class ProbeResult:
    name: str
    status: DependencyState
    detail: str


@dataclass(slots=True)
class DependencyProbe:
    name: str
    evaluator: Callable[[], ProbeResult]

    def check(self) -> ProbeResult:
        try:
            result = self.evaluator()
        except TimeoutError:
            return ProbeResult(
                name=self.name,
                status="degraded",
                detail="dependency probe timed out",
            )
        except Exception:
            return ProbeResult(
                name=self.name,
                status="degraded",
                detail="dependency probe failed",
            )

        if not isinstance(result, ProbeResult):
            return ProbeResult(
                name=self.name,
                status="degraded",
                detail="dependency probe returned malformed result",
            )

        if result.name != self.name or result.status not in {"ready", "degraded"}:
            return ProbeResult(
                name=self.name,
                status="degraded",
                detail="dependency probe returned malformed result",
            )

        return result


@dataclass(slots=True)
class ReadinessService:
    probes: list[DependencyProbe] = field(default_factory=list)

    def evaluate(self) -> list[ProbeResult]:
        return [probe.check() for probe in self.probes]


@dataclass(slots=True)
class ConfigurableProbeState:
    name: str = "chat-backend"
    mode: ProbeMode = "ready"

    def set_mode(self, mode: ProbeMode) -> None:
        self.mode = mode

    def evaluate(self) -> ProbeResult:
        if self.mode == "ready":
            return ProbeResult(name=self.name, status="ready", detail="dependency ready")
        if self.mode == "error":
            raise RuntimeError("probe failure")
        if self.mode == "timeout":
            raise TimeoutError("probe timeout")
        if self.mode == "malformed":
            return "broken"  # type: ignore[return-value]
        return ProbeResult(name=self.name, status="degraded", detail="dependency degraded")


def build_default_readiness_service() -> ReadinessService:
    state = ConfigurableProbeState()
    return ReadinessService(probes=[DependencyProbe(name=state.name, evaluator=state.evaluate)])
