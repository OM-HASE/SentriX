from pydantic import BaseModel
from typing import List, Dict, Any


class IncidentFingerprint(BaseModel):

    incident_id: str

    severity_score: float

    cognitive_complexity: float

    runtime_environment: Dict[str, Any]

    failure_signature_hash: str


class CausalAnalysisGraph(BaseModel):

    root_failure_node: str

    failure_propagation_chain: List[str]

    execution_dependencies: List[str]

    semantic_relationships: List[Dict[str, Any]]


class CognitiveReasoningTrace(BaseModel):

    retrieval_reasoning: List[str]

    graph_reasoning: List[str]

    symbolic_inference: List[str]

    llm_hypothesis_chain: List[str]


class CodeForensics(BaseModel):

    affected_artifacts: List[str]

    control_flow_breakpoints: List[str]

    vulnerable_execution_paths: List[str]

    state_transition_failures: List[str]


class RepositoryIntelligence(BaseModel):

    affected_services: List[str]

    cross_module_dependencies: List[str]

    architectural_impact_radius: List[str]

    risk_propagation_score: float


class RepairIntelligence(BaseModel):

    repair_strategy: Dict[str, Any]

    safe_fix_candidates: List[str]

    breaking_change_analysis: Dict[str, Any]

    autonomous_patch_plan: List[str]


class ValidationMatrix(BaseModel):

    reproduction_protocol: List[str]

    behavioral_assertions: List[str]

    regression_risk_vectors: List[str]

    recommended_test_scope: List[str]


class VisualizationPayload(BaseModel):

    graph_nodes: List[Dict[str, Any]]

    graph_edges: List[Dict[str, Any]]

    heat_zones: List[Dict[str, Any]]

    execution_timeline: List[Dict[str, Any]]


class CognitiveRCA(BaseModel):

    incident_fingerprint: IncidentFingerprint

    causal_analysis_graph: CausalAnalysisGraph

    cognitive_reasoning_trace: CognitiveReasoningTrace

    code_forensics: CodeForensics

    repository_intelligence: RepositoryIntelligence

    repair_intelligence: RepairIntelligence

    validation_matrix: ValidationMatrix

    visualization_payload: VisualizationPayload