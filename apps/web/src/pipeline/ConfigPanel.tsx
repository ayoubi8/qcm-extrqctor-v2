import { useMemo, useState } from "react";
import { Button, Card } from "../components/ui";
import { Step1ConfigPanel } from "./step1/Step1ConfigPanel";
import type { Step1Config } from "./step1/types";
import { Step2ConfigPanel } from "./step2/Step2ConfigPanel";
import type { Step2Config } from "./step2/types";
import { Step3CorrectionConfigPanel } from "./step3-correction/Step3CorrectionConfigPanel";
import type { Step3CorrectionConfig } from "./step3-correction/types";
import { Step4SimilarityConfigPanel } from "./step4-similarity/Step4SimilarityConfigPanel";
import type { Step4SimilarityConfig } from "./step4-similarity/types";
import type { PipelineRunContext, PipelineStepId } from "./types";

interface ConfigPanelProps {
  activeStepId: PipelineStepId;
  context: PipelineRunContext;
  onRunStep: (stepId: PipelineStepId, payload: Record<string, unknown>) => void;
}

export function ConfigPanel({ activeStepId, context, onRunStep }: ConfigPanelProps) {
  const [step1, setStep1] = useState<Step1Config>({ extractionMode: "automatic", textFixerEnabled: true });
  const [step2, setStep2] = useState<Step2Config>({
    pageBatchSize: 0,
    internalPageConcurrency: 5,
    extractionPromptId: "step2.page_qcm_extraction.v1",
    metadataDefaults: {},
    metadataStrategies: {},
    legacySubcategoryPolicy: "preserve_internal",
    templateName: "default",
    templateOverrides: {},
    outputFormat: "json+xlsx",
    model: { provider: "openrouter", primaryModelId: "configured-by-admin", fallbackModelIds: [] }
  });
  const [step3, setStep3] = useState<Step3CorrectionConfig>({
    mode: "page_detection",
    selectedPages: [],
    candidateThreshold: 15,
    includeNeighbors: true,
    forceOverwrite: false,
    visionDetections: {}
  });
  const [step4, setStep4] = useState<Step4SimilarityConfig>({
    referenceDbId: "",
    mode: "text_only",
    threshold: 0.75,
    textWeight: 0.7,
    correctionWeight: 0.3,
    colorGreen: 0.9,
    colorYellow: 0.75,
    exportExisting: false,
    exportQcmIds: []
  });

  const runPayload = useMemo(
    () => ({
      user_id: context.userId,
      project_id: context.projectId,
      run_id: context.runId,
      source_artifact_ids: context.sourceArtifactIds
    }),
    [context]
  );

  if (activeStepId === "step1") {
    return <Step1ConfigPanel value={step1} onChange={setStep1} onRun={() => onRunStep("step1", { ...runPayload, config: step1 })} />;
  }
  if (activeStepId === "step2") {
    return <Step2ConfigPanel value={step2} onChange={setStep2} onRun={() => onRunStep("step2", { ...runPayload, config: step2 })} />;
  }
  if (activeStepId === "step3-correction") {
    return <Step3CorrectionConfigPanel value={step3} onChange={setStep3} onRun={() => onRunStep("step3-correction", { ...runPayload, config: step3 })} />;
  }
  if (activeStepId === "step4-similarity") {
    return <Step4SimilarityConfigPanel value={step4} onChange={setStep4} onRun={() => onRunStep("step4-similarity", { ...runPayload, config: step4 })} />;
  }

  return (
    <Card title="Configuration">
      <Button disabled>Unavailable</Button>
    </Card>
  );
}
