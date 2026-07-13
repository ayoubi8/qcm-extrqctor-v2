"""Future Step 4 Similarity Match compatibility wrapper for legacy Step 8 semantics."""

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
import json
from typing import Any, Protocol

from qcm_application.artifact_service import checksum_bytes
from qcm_domain.reference_db import (
    DEFAULT_GREEN_BAND,
    DEFAULT_YELLOW_BAND,
    SimilarityMatchMode,
    normalize_match_mode,
    qcm_identity,
    similarity_band,
    validate_match_threshold,
    validate_match_weights,
)
from qcm_shared.contracts import ArtifactType, QualityStatus, RetentionPolicy, TerminalEventType, TerminalLevel
from qcm_shared.step4_contracts import (
    STEP4_SCHEMA_VERSION,
    Step4MatchSummary,
    Step4SimilarityQuality,
    Step4SimilarityResult,
    Step4SimilarityRunCommand,
)
from qcm_shared.storage_contracts import ArtifactWriteRequest
from qcm_shared.task_contracts import TerminalEventCreate


class Step4ArtifactSink(Protocol):
    def write(self, request: ArtifactWriteRequest) -> str:
        ...


class Step4TerminalSink(Protocol):
    def append(self, event: TerminalEventCreate) -> Any:
        ...


@dataclass(frozen=True, slots=True)
class Step4ArtifactRecord:
    artifact_id: str
    request: ArtifactWriteRequest


class InMemoryStep4ArtifactSink:
    def __init__(self) -> None:
        self.records: list[Step4ArtifactRecord] = []

    def write(self, request: ArtifactWriteRequest) -> str:
        self.records.append(Step4ArtifactRecord(artifact_id=request.artifact_id, request=request))
        return request.artifact_id


class Step4SimilarityService:
    def __init__(
        self,
        *,
        artifact_sink: Step4ArtifactSink | None = None,
        terminal_sink: Step4TerminalSink | None = None,
    ) -> None:
        self.artifact_sink = artifact_sink
        self.terminal_sink = terminal_sink

    def run(self, command: Step4SimilarityRunCommand) -> Step4SimilarityResult:
        _validate_command(command)
        mode = normalize_match_mode(command.config.mode)
        threshold = validate_match_threshold(command.config.threshold)
        text_weight, correction_weight = validate_match_weights(command.config.text_weight, command.config.correction_weight)
        self._emit(command, TerminalLevel.INFO, TerminalEventType.STEP_STARTED, "Step 4 similarity matching started")

        if command.config.export_existing:
            matches = tuple(dict(item) for item in command.existing_matches)
            warnings = ("Exported from existing similarity results without re-matching",)
        else:
            matches = tuple(
                _match_source_qcm(
                    source_qcm=source,
                    source_index=index,
                    reference_qcms=command.reference_qcms,
                    mode=mode,
                    threshold=threshold,
                    text_weight=text_weight,
                    correction_weight=correction_weight,
                    color_green=command.config.color_green,
                    color_yellow=command.config.color_yellow,
                )
                for index, source in enumerate(command.source_qcms, start=1)
            )
            warnings = ()

        exported_matches = _filter_export_matches(matches, command)
        summary = _summary(matches, threshold=threshold, mode=mode.value, green=command.config.color_green, yellow=command.config.color_yellow)
        quality = _quality(matches, warnings)

        artifact_ids: list[str] = []
        match_json_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step4-similarity-json",
            artifact_type=ArtifactType.STEP4_SIMILARITY_JSON,
            filename="step4-similarity-matches.json",
            content_type="application/json",
            content=_json_bytes({"summary": asdict(summary), "matches": list(matches)}),
            retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        )
        artifact_ids.append(match_json_id)
        match_xlsx_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step4-similarity-xlsx",
            artifact_type=ArtifactType.STEP4_SIMILARITY_XLSX,
            filename="step4-similarity-matches.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=_xlsx_placeholder_bytes(matches),
            retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
        )
        artifact_ids.append(match_xlsx_id)
        export_id = None
        if (
            command.config.export_existing
            or command.config.export_qcm_ids
            or command.config.export_min_similarity is not None
            or command.config.export_max_similarity is not None
        ):
            export_id = self._write_artifact(
                command,
                artifact_id=f"{command.run_id}-step4-export-existing",
                artifact_type=ArtifactType.STEP4_SIMILARITY_XLSX,
                filename="step4-export-existing.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=_xlsx_placeholder_bytes(exported_matches),
                retention_policy=RetentionPolicy.FINAL_UNTIL_PROJECT_DELETE,
            )
            artifact_ids.append(export_id)
        quality_id = self._write_artifact(
            command,
            artifact_id=f"{command.run_id}-step4-similarity-quality",
            artifact_type=ArtifactType.DEBUG_INTERNAL,
            filename="step4-similarity-quality.json",
            content_type="application/json",
            content=_json_bytes({"quality": asdict(quality) | {"status": quality.status.value}, "summary": asdict(summary)}),
            retention_policy=RetentionPolicy.DEBUG_SHORT_LIVED,
        )
        artifact_ids.append(quality_id)

        self._emit(
            command,
            TerminalLevel.WARNING if quality.warnings else TerminalLevel.SUCCESS,
            TerminalEventType.STEP_COMPLETED,
            "Step 4 similarity matching completed",
            {"matched_qcms": summary.matched_qcms, "mode": mode.value},
        )
        return Step4SimilarityResult(
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            matches=matches,
            exported_matches=exported_matches,
            summary=summary,
            quality=quality,
            artifact_ids=tuple(artifact_ids),
            match_json_artifact_id=match_json_id,
            match_xlsx_artifact_id=match_xlsx_id,
            export_artifact_id=export_id,
        )

    def _write_artifact(
        self,
        command: Step4SimilarityRunCommand,
        *,
        artifact_id: str,
        artifact_type: ArtifactType,
        filename: str,
        content_type: str,
        content: bytes,
        retention_policy: RetentionPolicy,
    ) -> str:
        request = ArtifactWriteRequest(
            user_id=command.user_id,
            project_id=command.project_id,
            run_id=command.run_id,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            filename=filename,
            content_type=content_type,
            content=content,
            version_number=1,
            checksum=checksum_bytes(content),
            schema_version=STEP4_SCHEMA_VERSION,
            retention_policy=retention_policy,
            source_artifact_ids=list(command.source_artifact_ids),
        )
        if self.artifact_sink is not None:
            return self.artifact_sink.write(request)
        return request.artifact_id

    def _emit(
        self,
        command: Step4SimilarityRunCommand,
        level: TerminalLevel,
        event_type: TerminalEventType,
        message: str,
        safe_payload: dict[str, Any] | None = None,
    ) -> None:
        if self.terminal_sink is None:
            return
        self.terminal_sink.append(
            TerminalEventCreate(
                user_id=command.user_id,
                project_id=command.project_id,
                run_id=command.run_id,
                task_id=command.task_id,
                attempt_id=command.attempt_id,
                level=level,
                event_type=event_type,
                message=message,
                safe_payload=safe_payload or {},
            )
        )


def _validate_command(command: Step4SimilarityRunCommand) -> None:
    if not command.user_id or not command.project_id or not command.run_id:
        raise ValueError("Step 4 similarity requires owner, project, and run identifiers")
    if not command.source_artifact_ids:
        raise ValueError("Step 4 similarity requires source artifact identifiers")
    if not command.source_qcms and not command.config.export_existing:
        raise ValueError("Step 4 similarity requires source QCMs")
    if not command.reference_qcms and not command.config.export_existing:
        raise ValueError("Step 4 similarity requires a private reference DB")


def _match_source_qcm(
    *,
    source_qcm: dict[str, Any],
    source_index: int,
    reference_qcms: tuple[dict[str, Any], ...],
    mode: SimilarityMatchMode,
    threshold: float,
    text_weight: float,
    correction_weight: float,
    color_green: float,
    color_yellow: float,
) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for ref_index, ref_qcm in enumerate(reference_qcms, start=1):
        text_score = _ratio(_build_text(source_qcm), _build_text(ref_qcm))
        corr_score = _ratio(_correction(source_qcm), _correction(ref_qcm)) if _correction(source_qcm) or _correction(ref_qcm) else 0.0
        if mode == SimilarityMatchMode.WEIGHTED:
            score = text_weight * text_score + correction_weight * corr_score
        elif mode == SimilarityMatchMode.FULL:
            score = _ratio(_build_full(source_qcm), _build_full(ref_qcm))
        else:
            score = text_score
        if best is None or score > best["best_match"]["similarity"]:
            best = {
                "source_id": qcm_identity(source_qcm, source_index),
                "source_qcm": dict(source_qcm),
                "best_match": {
                    "similarity": round(score, 4),
                    "band": similarity_band(score, green=color_green, yellow=color_yellow),
                    "text_similarity": round(text_score, 4),
                    "corr_similarity": round(corr_score, 4) if mode == SimilarityMatchMode.WEIGHTED else None,
                    "mode": mode.value,
                    "ref_id": qcm_identity(ref_qcm, ref_index),
                    "ref_qcm": dict(ref_qcm),
                },
            }
    if best is None or best["best_match"]["similarity"] < threshold:
        return {
            "source_id": qcm_identity(source_qcm, source_index),
            "source_qcm": dict(source_qcm),
            "best_match": {
                "similarity": 0.0,
                "band": "red",
                "text_similarity": 0.0,
                "corr_similarity": 0.0 if mode == SimilarityMatchMode.WEIGHTED else None,
                "mode": mode.value,
                "ref_id": None,
                "ref_qcm": {},
            },
        }
    return best


def _filter_export_matches(matches: tuple[dict[str, Any], ...], command: Step4SimilarityRunCommand) -> tuple[dict[str, Any], ...]:
    selected_ids = set(command.config.export_qcm_ids)
    min_score = 0.0 if command.config.export_min_similarity is None else command.config.export_min_similarity
    max_score = 1.0 if command.config.export_max_similarity is None else command.config.export_max_similarity
    return tuple(
        match
        for match in matches
        if (not selected_ids or match["source_id"] in selected_ids)
        and min_score <= match["best_match"]["similarity"] <= max_score
    )


def _summary(matches: tuple[dict[str, Any], ...], *, threshold: float, mode: str, green: float, yellow: float) -> Step4MatchSummary:
    scores = [match["best_match"]["similarity"] for match in matches]
    matched = [score for score in scores if score >= threshold]
    return Step4MatchSummary(
        total_source_qcms=len(matches),
        matched_qcms=len(matched),
        green_matches=sum(1 for score in matched if score >= green),
        yellow_matches=sum(1 for score in matched if yellow <= score < green),
        red_matches=sum(1 for score in matched if score < yellow),
        average_similarity=round(sum(scores) / len(scores), 4) if scores else 0.0,
        threshold=threshold,
        mode=mode,
    )


def _quality(matches: tuple[dict[str, Any], ...], warnings: tuple[str, ...]) -> Step4SimilarityQuality:
    local_warnings = list(warnings)
    if not any(match["best_match"]["ref_qcm"] for match in matches):
        local_warnings.append("No matches found above the configured threshold")
    status = QualityStatus.PASSED_WITH_WARNINGS if local_warnings else QualityStatus.PASSED
    return Step4SimilarityQuality(status=status, warnings=tuple(dict.fromkeys(local_warnings)))


def _build_text(qcm: dict[str, Any]) -> str:
    parts = [str(qcm.get("Text") or qcm.get("text") or "")]
    propositions = qcm.get("propositions") or {}
    for key in ("A", "B", "C", "D", "E"):
        parts.append(str(qcm.get(key) or propositions.get(key) or propositions.get(key.lower()) or ""))
    return _normalize(" ".join(parts))


def _build_full(qcm: dict[str, Any]) -> str:
    return _normalize(f"{_build_text(qcm)} {_correction(qcm)}")


def _correction(qcm: dict[str, Any]) -> str:
    return _normalize(qcm.get("Correct") or qcm.get("correct") or "")


def _normalize(value: Any) -> str:
    return " ".join(str(value).lower().split())


def _ratio(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _xlsx_placeholder_bytes(matches: tuple[dict[str, Any], ...]) -> bytes:
    rows = ["ID,Similarity,Band,Mode,RefID"]
    for match in matches:
        best = match["best_match"]
        rows.append(f'{match["source_id"]},{best["similarity"]},{best["band"]},{best["mode"]},{best.get("ref_id") or ""}')
    return ("\n".join(rows) + "\n").encode("utf-8")
