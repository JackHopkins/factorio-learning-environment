"""Construction and projection helpers for certified factory capability.

This module deliberately keeps evidence collection separate from the game
runner. A snapshot helper can only issue commissioning evidence. Callers must
provide an explicit frozen qualification result to issue an autonomous or
robust certificate.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from fle.envd.models import (
    CapabilityCertificate,
    CapabilityLedger,
    ContractContextSnapshot,
    ContractEpochOutcome,
    ContractEpochSpec,
    FactoryProgressVector,
)


def _rate_map(snapshot: ContractContextSnapshot) -> dict[str, float]:
    """Use the longest available passive window for commissioning evidence."""
    products = set(snapshot.production_rates_60s) | set(snapshot.production_rates_300s)
    return {
        product: max(
            float(snapshot.production_rates_60s.get(product, 0.0)),
            float(snapshot.production_rates_300s.get(product, 0.0)),
        )
        for product in sorted(products)
        if max(
            float(snapshot.production_rates_60s.get(product, 0.0)),
            float(snapshot.production_rates_300s.get(product, 0.0)),
        ) > 0
    }


def commissioning_certificate(
    snapshot: ContractContextSnapshot,
    *,
    product: str,
    rate_per_minute: float | None = None,
    capability_band: int = 0,
    prerequisite_capability_ids: Iterable[str] = (),
    certificate_id: str | None = None,
) -> CapabilityCertificate:
    """Create passive commissioning evidence for one product.

    Even a positive 60-second production rate remains ``commissioned``. It
    cannot be passed as autonomous evidence by changing a flag on the record.
    """
    rate = (
        float(rate_per_minute)
        if rate_per_minute is not None
        else max(
            float(snapshot.production_rates_60s.get(product, 0.0)),
            float(snapshot.production_rates_300s.get(product, 0.0)),
        )
    )
    return CapabilityCertificate(
        certificate_id=certificate_id or f"commissioned:{snapshot.captured_tick}:{product}",
        capability_id=f"product:{product}",
        session_id=snapshot.session_id,
        source_state_digest=snapshot.state_digest,
        captured_tick=snapshot.captured_tick,
        status="commissioned",
        evidence_source="snapshot",
        demand_vector={product: max(rate, 0.0)},
        observed_rate_per_minute={product: max(rate, 0.0)},
        capability_band=capability_band,
        prerequisite_capability_ids=tuple(prerequisite_capability_ids),
        reliability=0.0,
        evidence={"passive_window_ticks": 60 * 60},
    )


def commissioning_certificates(
    snapshot: ContractContextSnapshot,
    *,
    capability_bands: Mapping[str, int] | None = None,
    prerequisites: Mapping[str, Iterable[str]] | None = None,
) -> list[CapabilityCertificate]:
    """Create one commissioning certificate for each observed product."""
    capability_bands = capability_bands or {}
    prerequisites = prerequisites or {}
    return [
        commissioning_certificate(
            snapshot,
            product=product,
            rate_per_minute=rate,
            capability_band=int(capability_bands.get(product, 0)),
            prerequisite_capability_ids=prerequisites.get(product, ()),
        )
        for product, rate in _rate_map(snapshot).items()
    ]


def qualification_certificate(
    *,
    certificate_id: str,
    session_id: str = "",
    source_state_digest: str = "",
    captured_tick: int = 0,
    demand_vector: Mapping[str, float],
    target_rate_per_minute: Mapping[str, float] | None = None,
    observed_rate_per_minute: Mapping[str, float] | None = None,
    capability_band: int = 0,
    prerequisite_capability_ids: Iterable[str] = (),
    sustained_window_ticks: int,
    qualification_window_ticks: int,
    interventions_during_window: int = 0,
    reliability: float = 1.0,
    robust: bool = False,
    robustness_checks: int = 0,
    evidence: Mapping[str, Any] | None = None,
) -> CapabilityCertificate:
    """Issue an autonomous/robust certificate from a frozen run result.

    This is intentionally explicit rather than promoting a contract outcome:
    the caller has to state the qualification window and intervention count.
    Pydantic validation rejects all dishonest combinations.
    """
    observed = dict(observed_rate_per_minute or demand_vector)
    return CapabilityCertificate(
        certificate_id=certificate_id,
        session_id=session_id,
        source_state_digest=source_state_digest,
        captured_tick=captured_tick,
        certified_at_tick=captured_tick + qualification_window_ticks,
        status="robust" if robust else "autonomous",
        evidence_source="stress" if robust else "qualification",
        demand_vector=dict(demand_vector),
        target_rate_per_minute=dict(target_rate_per_minute or demand_vector),
        observed_rate_per_minute=observed,
        capability_band=capability_band,
        prerequisite_capability_ids=tuple(prerequisite_capability_ids),
        sustained_window_ticks=sustained_window_ticks,
        qualification_window_ticks=qualification_window_ticks,
        interventions_during_window=interventions_during_window,
        autonomous_validation=True,
        robustness_checks=robustness_checks,
        reliability=reliability,
        evidence=dict(evidence or {}),
    )


def contract_certificate(
    spec: ContractEpochSpec,
    outcome: ContractEpochOutcome,
) -> CapabilityCertificate:
    """Convert authoritative customer evidence without claiming autonomy.

    A one-shot result proves only commissioning. A sustained order records an
    observed service capability because the model was still allowed to act
    during its window. Promotion to autonomous remains exclusive to
    :func:`qualification_certificate`.
    """
    products = spec.products or ()
    if not products:
        demand_quantities = {spec.item_name: float(spec.quantity)}
    else:
        demand_quantities = {
            line.product: float(line.quantity) for line in products
        }
    window_minutes = max(float(spec.deadline_ticks) / 3600.0, 1e-9)
    target_rates = {
        product: quantity / window_minutes
        for product, quantity in demand_quantities.items()
    }
    delivered = dict(outcome.delivered_by_product or {})
    if not delivered:
        delivered = {spec.item_name: float(outcome.delivered_quantity)}
    observed_rates = {
        product: max(float(delivered.get(product, 0.0)), 0.0) / window_minutes
        for product in demand_quantities
    }
    sustained = spec.order_kind == "sustained"
    qualification = outcome.autonomous_throughput
    autonomous = bool(
        sustained
        and qualification is not None
        and qualification.authoritative
        and qualification.interventions_during_window == 0
        and qualification.performance_score >= 0.60
        and float(outcome.performance_score or outcome.completion_ratio) >= 0.60
    )
    if autonomous and qualification is not None:
        observed_rates = dict(qualification.observed_rate_per_minute)
    target_path = ()
    delta = outcome.capability_delta
    if delta is not None:
        raw_path = delta.evidence.get("target_path", ())
        target_path = tuple(
            node for node in raw_path
            if str(node).startswith("product:")
            and str(node).removeprefix("product:") not in demand_quantities
        )
    return CapabilityCertificate(
        certificate_id=f"contract:{spec.session_id}:{spec.epoch_index}",
        session_id=spec.session_id,
        source_state_digest=outcome.terminal_state_digest,
        captured_tick=spec.context.captured_tick,
        certified_at_tick=spec.context.captured_tick + outcome.simulation_ticks_used,
        status=(
            "autonomous"
            if autonomous
            else ("observed_sustained" if sustained else "commissioned")
        ),
        evidence_source="qualification" if autonomous else "contract",
        demand_vector=target_rates,
        target_rate_per_minute=target_rates,
        observed_rate_per_minute=observed_rates,
        capability_band=int(outcome.target_band or spec.target_band or 0),
        prerequisite_capability_ids=target_path,
        sustained_window_ticks=spec.deadline_ticks if sustained else 0,
        qualification_window_ticks=(
            qualification.window_ticks
            if autonomous and qualification is not None
            else 0
        ),
        interventions_during_window=(0 if autonomous else outcome.interventions_used),
        autonomous_validation=autonomous,
        reliability=(
            min(
                float(outcome.performance_score or outcome.completion_ratio),
                float(qualification.performance_score),
            )
            if autonomous and qualification is not None
            else float(outcome.performance_score or outcome.completion_ratio)
        ),
        evidence={
            "epoch_index": spec.epoch_index,
            "status": outcome.status,
            "completion_ratio": outcome.completion_ratio,
            "order_kind": spec.order_kind,
            "autonomous_throughput": (
                qualification.model_dump(mode="json")
                if qualification is not None
                else None
            ),
        },
    )


def ledger_from_epochs(epochs: Iterable[Any]) -> CapabilityLedger:
    """Rebuild the observed capability ledger from persisted epoch records."""
    epochs = list(epochs)
    session_id = epochs[0].spec.session_id if epochs else ""
    ledger = CapabilityLedger(session_id=session_id)
    for epoch in epochs:
        ledger.record(contract_certificate(epoch.spec, epoch.outcome))
    return ledger


def record_snapshot(
    ledger: CapabilityLedger,
    snapshot: ContractContextSnapshot,
    **kwargs: Any,
) -> list[CapabilityCertificate]:
    """Record passive snapshot evidence without awarding autonomy."""
    certificates = commissioning_certificates(snapshot, **kwargs)
    for certificate in certificates:
        ledger.record(certificate)
    return certificates


def progress_vector(ledger: CapabilityLedger) -> FactoryProgressVector:
    """Return the current vector with the ledger's best real watermark."""
    current = ledger.current_progress()
    if ledger.best_progress is not None:
        current.best_watermark = ledger.best_progress.model_dump(mode="json")
    return current


__all__ = [
    "commissioning_certificate",
    "commissioning_certificates",
    "contract_certificate",
    "ledger_from_epochs",
    "qualification_certificate",
    "record_snapshot",
    "progress_vector",
]
