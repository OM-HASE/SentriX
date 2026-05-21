import json
import uuid
import hashlib
import logging
import ollama

from app.rag.retriever import (
    retrieve_relevant_chunks
)

from app.graph.enriched_context_builder import (
    build_enriched_context
)

from app.graph.graph_memory import (
    repository_graph_memory
)

from app.graph.graph_builder import (
    build_repository_graph
)

from app.cognition.execution_cognition_engine import (
    build_execution_cognition
)

from app.cognition.symbolic_validation_engine import (
    SymbolicValidationEngine
)

from app.cognition.semantic_anomaly_engine import (
    SemanticAnomalyEngine
)

from app.cognition.runtime_cognition_engine import (
    RuntimeCognitionEngine
)

from app.cognition.failure_propagation_engine import (
    FailurePropagationEngine
)

from app.cognition.cross_file_cognition_engine import (
    CrossFileCognitionEngine
)

from app.cognition.confidence_cognition_engine import (
    ConfidenceCognitionEngine
)

from app.cognition.failure_clustering_engine import (
    FailureClusteringEngine
)

from app.cognition.repository_context_expansion_engine import (
    RepositoryContextExpansionEngine
)

from app.cognition.semantic_prioritization_engine import (
    SemanticPrioritizationEngine
)

from app.cognition.failure_graph_engine import (
    FailureGraphEngine
)

from app.intelligence.universal_symbol_resolver import (
    UniversalSymbolResolver
)

# NEW — stack trace mapper
from app.intelligence.stack_trace_mapper import (
    StackTraceMapper
)

logger = logging.getLogger(__name__)

# =========================================
# SIGNATURE HASH
# =========================================

def generate_signature_hash(text):
    return hashlib.md5(text.encode()).hexdigest()


# =========================================
# SAFE OLLAMA CALL
# =========================================

def generate_reasoning_trace(
    error_log,
    source_code,
    context_text,
    execution_cognition,
    symbolic_findings,
    stack_trace_mapping=None   # NEW parameter
):

    # Build stack trace section for the prompt
    stack_trace_section = ""
    if stack_trace_mapping and stack_trace_mapping.get("frame_count", 0) > 0:
        stack_trace_section = f"""
STACK TRACE MAPPING:
Language   : {stack_trace_mapping.get('language', 'unknown')}
Error Type : {stack_trace_mapping.get('error_type', '')}
Error Msg  : {stack_trace_mapping.get('error_message', '')}

Failure Root (most likely origin):
{json.dumps(stack_trace_mapping.get('failure_root'), indent=2)}

All Mapped Frames:
{json.dumps(stack_trace_mapping.get('mapped_frames', [])[:6], indent=2)}

Affected Files: {stack_trace_mapping.get('affected_files', [])}
Affected Graph Nodes: {stack_trace_mapping.get('affected_nodes', [])}
"""

    prompt = f"""
You are a senior software systems engineer with 30+ years of experience working on:
- distributed systems at AMD
- compiler infrastructure at NVIDIA
- runtime debugging at Apple
- large-scale backend systems
- static analysis engines
- production failure diagnostics

Your task is to perform deep semantic root cause analysis using ONLY the provided evidence.

Focus on:
- semantic inconsistencies
- unresolved method calls
- dependency anomalies
- graph relationships
- symbolic failures
- execution flow risks
- stack trace frame evidence (when provided)

Do NOT speculate beyond the provided evidence.

If evidence is insufficient, explicitly state:
"Insufficient evidence for deeper failure attribution."

Treat:
- unresolved semantic methods
- anomalous graph relationships
- inconsistent dependency usage

as likely symbolic failures.

Keep reasoning:
- concise
- technical
- evidence-grounded
- engineering-focused

IMPORTANT:
- Standard library imports are usually valid.
- Do not treat common runtime calls as failures unless evidence suggests so.
- Prioritize symbolic anomalies over speculative runtime assumptions.
- When stack trace mapping is provided, use the failure_root frame as the primary anchor.

FORMAT STRICTLY:

[ROOT_CAUSE]
Short root cause summary.

[EXECUTION_ANALYSIS]
Execution flow analysis.

[FAILURE_PROPAGATION]
Failure propagation reasoning.

[DEPENDENCY_ANALYSIS]
Dependency and semantic relationship analysis.

[REPAIR_PLAN]
Concrete repair recommendation.

[RISK_ANALYSIS]
Potential system risks.

ERROR LOG:
{error_log}

SOURCE CODE:
{source_code}

GRAPH CONTEXT:
{context_text}
{stack_trace_section}
EXECUTION COGNITION:
{json.dumps(execution_cognition, indent=2)}

SYMBOLIC FINDINGS:
{json.dumps(symbolic_findings, indent=2)}
"""

    response = ollama.chat(
        model="qwen2.5-coder:7b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        stream=False,
        options={
            "temperature": 0.00,
            "top_p": 0.85,
            "num_predict": 800
        }
    )

    return response["message"]["content"]


# =========================================
# SECTION EXTRACTION
# =========================================

def extract_section(text, section_name):

    start_token = f"[{section_name}]"
    start_idx = text.find(start_token)

    if start_idx == -1:
        return ""

    remaining = text[start_idx + len(start_token):]
    next_section = remaining.find("[")

    if next_section == -1:
        return remaining.strip()

    return remaining[:next_section].strip()


# =========================================
# FAILURE GRAPH GENERATION
# =========================================

def build_failure_graph(execution_cognition, findings=None, propagation=None):

    findings   = findings or []
    propagation = propagation or {}

    nodes = []
    edges = []
    node_registry = set()

    def add_node(node_id, node_type, label=None):
        if not node_id:
            return
        if node_id in node_registry:
            return
        node_registry.add(node_id)
        nodes.append({
            "id":    node_id,
            "label": label or node_id,
            "type":  node_type
        })

    for finding in findings:
        object_name = finding.get("object")
        method_name = (
            finding.get("method")
            or finding.get("invalid_method")
        )
        node_name  = finding.get("node")
        issue_type = finding.get("issue_type", "semantic_failure")

        if object_name:
            add_node(node_id=object_name, node_type="failure_object")
        if method_name:
            add_node(node_id=method_name, node_type="failure_method")
        if node_name:
            add_node(node_id=node_name, node_type="failure_node")

        if object_name and method_name:
            edges.append({
                "source":       object_name,
                "target":       method_name,
                "relationship": issue_type
            })

    for edge in execution_cognition.get("execution_flow", []):
        source       = edge.get("source")
        target       = edge.get("target")
        relationship = edge.get("relationship", "executes")

        if source:
            add_node(node_id=source, node_type="execution_node")
        if target:
            add_node(node_id=target, node_type="execution_node")
        if source and target:
            edges.append({
                "source":       source,
                "target":       target,
                "relationship": relationship
            })

    for path in propagation.get("propagation_paths", []):
        source       = path.get("source")
        target       = path.get("target")
        relationship = path.get("relationship", "propagates_to")

        if source:
            add_node(node_id=source, node_type="propagation_node")
        if target:
            add_node(node_id=target, node_type="propagation_node")
        if source and target:
            edges.append({
                "source":       source,
                "target":       target,
                "relationship": relationship
            })

    return {"nodes": nodes, "edges": edges}



# =========================================
# SEVERITY ENGINE
# =========================================

def _compute_severity(
    findings: list,
    confidence: dict,
    stack_trace: dict,
    error_type: str
) -> str:
    """
    Computes severity from actual evidence, not hardcoded.

    critical : NoneType crash + multiple files affected, or
               confidence > 0.7 + null_dereference
    high     : clear unresolved method, AttributeError, crash
    medium   : orphan nodes, dangling refs, low confidence
    low      : style / informational anomalies only
    """
    none_findings   = [f for f in findings if f.get("issue_type") == "none_type_method_call"]
    unresolved      = [f for f in findings if f.get("issue_type") == "unresolved_method"]
    affected_files  = len(stack_trace.get("affected_files", []))
    overall_conf    = confidence.get("overall_confidence", 0.0)

    crash_errors = {
        "AttributeError", "NullPointerException", "NullReferenceException",
        "null_dereference_failure", "attribute_error", "TypeError",
        "SegmentationFault", "panic",
    }

    is_crash = (
        error_type in crash_errors
        or any(x in error_type for x in ["Error", "Exception", "Fault"])
    )

    if none_findings and (affected_files > 1 or overall_conf > 0.6):
        return "critical"
    if none_findings or (unresolved and is_crash):
        return "high"
    if unresolved or is_crash:
        return "high"
    if findings and overall_conf > 0.3:
        return "medium"
    if findings:
        return "medium"
    return "low"


# =========================================
# MAIN HYBRID COGNITIVE RCA
# =========================================

def analyze_graph_root_cause(error_log, source_code):

    # =====================================
    # STACK TRACE MAPPING  (NEW)
    # Maps traceback frames → graph nodes
    # before any other reasoning step so
    # the LLM gets precise file/line/node
    # context instead of guessing.
    # =====================================

    mapper = StackTraceMapper()
    trace_result = mapper.map(error_log)
    stack_trace_mapping = mapper.to_dict(trace_result)

    logger.debug(
        "Stack trace mapping: %d frames, root=%s",
        stack_trace_mapping.get("frame_count", 0),
        stack_trace_mapping.get("failure_root"),
    )

    # =====================================
    # SEMANTIC RETRIEVAL
    # =====================================

    combined_query = f"""
ERROR LOG:
{error_log}

SOURCE CODE:
{source_code}
"""

    retrieved = retrieve_relevant_chunks(combined_query, top_k=5)

    if isinstance(retrieved, list):
        retrieved_chunks = retrieved
    else:
        retrieved_chunks = retrieved["documents"][0]

    # =====================================
    # ENRICHED CONTEXT
    # =====================================

    enriched_context = build_enriched_context(retrieved_chunks)

    context_text = json.dumps(enriched_context, indent=2)
    context_text = context_text[:4000]

    # =====================================
    # ACTIVE GRAPH
    # Inject source_code into raw_source node metadata
    # so NoneType scanner (Pass 3 in SymbolicValidationEngine)
    # can find "self.x = None" assignments in submitted code.
    # =====================================

    active_graph = repository_graph_memory.get("active_graph", {})

    if source_code and source_code.strip():
        nodes = active_graph.get("nodes", {})
        if "source_code" in nodes:
            nodes["source_code"].setdefault("metadata", {})["source_code"] = source_code
        else:
            nodes["_submitted_source"] = {
                "type": "raw_source",
                "metadata": {"source_code": source_code, "synthetic": False}
            }

    # Propagate detected language into graph so SymbolicValidationEngine
    # can apply language-specific stdlib filtering
    detected_lang = stack_trace_mapping.get("language", "unknown")
    if not detected_lang or detected_lang == "unknown":
        # Fallback: infer from source_code patterns
        sc_lower = (source_code or "").lower()
        if "console.log" in sc_lower or "const " in sc_lower or "=>" in sc_lower or "function " in sc_lower:
            detected_lang = "javascript"
        elif "def " in sc_lower and "self" in sc_lower:
            detected_lang = "python"
        elif "public class" in sc_lower or "system.out" in sc_lower:
            detected_lang = "java"
        elif "package main" in sc_lower or "fmt.println" in sc_lower:
            detected_lang = "go"
        elif "fn main" in sc_lower or "let mut" in sc_lower:
            detected_lang = "rust"
    if detected_lang and detected_lang != "unknown":
        active_graph["language"] = detected_lang

    # =====================================
    # REPOSITORY CONTEXT EXPANSION
    # =====================================

    expanded_context = (
        RepositoryContextExpansionEngine(
            repository_graph_memory.get("repository_index", [])
        )
        .expand_context(source_code)
    )

    expanded_files = expanded_context.get("expanded_files", [])

    for expanded_file in expanded_files:
        expanded_source = expanded_file.get("source_code", "")
        if expanded_source:
            build_repository_graph(expanded_source)

    active_graph = repository_graph_memory.get("active_graph", {})

    # =====================================
    # EXECUTION COGNITION
    # =====================================

    execution_cognition = build_execution_cognition(
        error_log, source_code, active_graph
    )

    execution_flow = execution_cognition.get("execution_flow", [])

    # =====================================
    # UNIVERSAL SYMBOL RESOLUTION
    # =====================================

    semantic_relationships = active_graph.get("semantic_relationships", [])
    code_entities          = active_graph.get("code_entities", [])

    symbolic_findings = (
        UniversalSymbolResolver(
            semantic_relationships=semantic_relationships,
            code_entities=code_entities,
            language=active_graph.get("language", "unknown")
        )
        .analyze_symbolic_failures()
    )

    # =====================================
    # SYMBOLIC VALIDATION
    # =====================================

    validator         = SymbolicValidationEngine(active_graph)
    validated_findings = validator.validate_symbols()

    for finding in validated_findings:
        symbol = finding.get("symbol")
        if not any(e.get("symbol") == symbol for e in symbolic_findings):
            symbolic_findings.append(finding)

    # =====================================
    # COMPATIBILITY FINDINGS
    # =====================================

    compatibility_findings = active_graph.get("compatibility_findings", [])

    for finding in compatibility_findings:
        invalid_method = finding.get("invalid_method")
        object_name    = finding.get("object")
        symbol         = f"{object_name}.{invalid_method}"
        finding["symbol"] = symbol
        if "method" not in finding:
            finding["method"] = invalid_method
        if not any(e.get("symbol") == symbol for e in symbolic_findings):
            symbolic_findings.append(finding)

    # =====================================
    # SEMANTIC ANOMALIES
    # =====================================

    semantic_anomalies = (
        SemanticAnomalyEngine(active_graph).detect_anomalies()
    )

    all_findings = symbolic_findings + semantic_anomalies

    all_findings = (
        SemanticPrioritizationEngine(all_findings).prioritize_findings()
    )

    # =====================================
    # GRAPH DATA
    # =====================================

    graph_nodes = []
    graph_edges = []

    if active_graph:
        for node_name, node_data in active_graph.get("nodes", {}).items():
            graph_nodes.append({
                "id":   node_name,
                "type": node_data.get("type")
            })
        graph_edges = active_graph.get("edges", [])

    # =====================================
    # RUNTIME COGNITION
    # =====================================

    runtime_cognition = (
        RuntimeCognitionEngine(active_graph, all_findings, execution_flow)
        .analyze_runtime_cognition()
    )

    execution_cognition["runtime_breakpoints"] = runtime_cognition.get(
        "runtime_breakpoints", []
    )
    execution_cognition["state_failures"] = runtime_cognition.get(
        "state_failures", []
    )

    # =====================================
    # PROPAGATION ANALYSIS
    # =====================================

    propagation_analysis = (
        FailurePropagationEngine(active_graph, all_findings)
        .analyze_propagation()
    )
    execution_cognition["propagation_analysis"] = propagation_analysis

    # =====================================
    # CROSS FILE ANALYSIS
    # =====================================

    cross_file_analysis = (
        CrossFileCognitionEngine(active_graph, all_findings)
        .analyze_cross_file_impact()
    )
    execution_cognition["cross_file_analysis"] = cross_file_analysis

    # =====================================
    # CONFIDENCE ANALYSIS
    # =====================================

    confidence_analysis = (
        ConfidenceCognitionEngine(
            active_graph, all_findings,
            runtime_cognition, propagation_analysis, cross_file_analysis,
            stack_trace_mapping=stack_trace_mapping  # NEW: boosts confidence score
        )
        .analyze_confidence()
    )
    execution_cognition["confidence_analysis"] = confidence_analysis

    # =====================================
    # FAILURE CLUSTERING
    # =====================================

    failure_clustering = (
        FailureClusteringEngine(all_findings, propagation_analysis)
        .cluster_failures()
    )
    execution_cognition["failure_clusters"] = failure_clustering

    # =====================================
    # FILTER NULL EDGES  (cleanup)
    # Null edges appear when execution_cognition has a
    # stage-only entry with no source/target. They pollute
    # every graph output. Strip them once here.
    # =====================================

    def _clean_edges(edges):
        return [
            e for e in (edges or [])
            if e.get("source") and e.get("target")
        ]

    execution_cognition["execution_flow"] = _clean_edges(
        execution_cognition.get("execution_flow", [])
    )
    if active_graph.get("edges"):
        active_graph["edges"] = _clean_edges(active_graph["edges"])

    # =====================================
    # FAILURE GRAPH
    # =====================================

    base_failure_graph = build_failure_graph(
        execution_cognition,
        findings=all_findings,
        propagation=propagation_analysis
    )

    failure_graph = (
        FailureGraphEngine(
            execution_flow, execution_cognition, propagation_analysis
        ).build_failure_graph()
    )
    failure_graph["base_graph"] = base_failure_graph

    # =====================================
    # FOCUS FINDINGS — cap at top 5
    # When we have a specific failure function from stack trace
    # (e.g. "ad", "puhs", "apend"), prioritize the finding that
    # matches it so the LLM gets focused evidence, not noise.
    # =====================================

    focus_method = (
        stack_trace_mapping.get("failure_root") or {}
    ).get("function", "")

    if focus_method and focus_method not in ("<compiler_error>", "unknown"):
        # Put findings that match the failing method first
        priority = [
            f for f in all_findings
            if f.get("method") == focus_method
            or focus_method in (f.get("symbol") or "")
        ]
        rest = [f for f in all_findings if f not in priority]
        focused_findings = (priority + rest)[:5]
    else:
        focused_findings = all_findings[:5]

    # Truncate source_code for LLM — keep area around failure line
    failure_line = (
        stack_trace_mapping.get("failure_root") or {}
    ).get("line")
    sc_for_llm = source_code or ""
    if len(sc_for_llm) > 1800:
        if failure_line and isinstance(failure_line, int):
            lines = sc_for_llm.splitlines()
            s = max(0, failure_line - 20)
            e = min(len(lines), failure_line + 15)
            sc_for_llm = "... [truncated] ...\n" + "\n".join(lines[s:e]) + "\n... [truncated]"
        else:
            sc_for_llm = sc_for_llm[:1800] + "\n... [truncated for context]"

    # Truncate error_log
    el_for_llm = (error_log or "")[:900]
    if len(error_log or "") > 900:
        el_for_llm += "\n... [truncated]"

    # =====================================
    # LLM REASONING (stack trace injected)
    # =====================================

    reasoning_trace = generate_reasoning_trace(
        el_for_llm,
        sc_for_llm,
        context_text,
        execution_cognition,
        focused_findings,
        stack_trace_mapping=stack_trace_mapping
    )

    # =====================================
    # ERROR TYPE
    # =====================================

    # --- derive error_type from evidence ---
    _st_error = stack_trace_mapping.get("error_type", "")
    _none_findings = [f for f in all_findings if f.get("issue_type") == "none_type_method_call"]
    _unresolved    = [f for f in all_findings if f.get("issue_type") == "unresolved_method"]

    if _none_findings:
        error_type = "null_dereference_failure"
    elif _unresolved:
        error_type = "symbolic_failure"
    elif _st_error:
        error_type = _st_error          # e.g. "AttributeError", "NullPointerException"
    elif "AttributeError" in error_log or "NullPointerException" in error_log:
        error_type = "attribute_error"
    elif "ImportError" in error_log or "ModuleNotFoundError" in error_log:
        error_type = "import_error"
    elif "TypeError" in error_log:
        error_type = "type_error"
    elif "KeyError" in error_log or "IndexError" in error_log:
        error_type = "index_key_error"
    else:
        error_type = "runtime_failure"

    # =====================================
    # FINAL RCA
    # =====================================

    cognitive_rca = {

        "incident": {
            "incident_id":            str(uuid.uuid4()),
            "severity":               _compute_severity(
                                          all_findings,
                                          confidence_analysis,
                                          stack_trace_mapping,
                                          error_type,
                                      ),
            "failure_signature_hash": generate_signature_hash(error_log),
            "error_type":             error_type
        },

        "root_cause": {
            "summary": extract_section(reasoning_trace, "ROOT_CAUSE")
        },

        # NEW — precise frame-to-node mapping
        "stack_trace_mapping": stack_trace_mapping,

        "execution_cognition": execution_cognition,

        "failure_graph": failure_graph,

        "reasoning_trace": {
            "execution_analysis":  extract_section(reasoning_trace, "EXECUTION_ANALYSIS"),
            "failure_propagation": extract_section(reasoning_trace, "FAILURE_PROPAGATION"),
            "dependency_analysis": extract_section(reasoning_trace, "DEPENDENCY_ANALYSIS"),
        },

        "repair_plan": {
            "recommended_fix": extract_section(reasoning_trace, "REPAIR_PLAN")
        },

        "impact_analysis": {
            "risk_analysis": extract_section(reasoning_trace, "RISK_ANALYSIS")
        },

        "symbolic_findings": all_findings,

        "repository_context": {
            "semantic_nodes": graph_nodes,
            "semantic_edges": graph_edges
        },

        "visualization_payload": {
            "semantic_graph": {
                "nodes": graph_nodes,
                "edges": graph_edges
            }
        }
    }

    return cognitive_rca