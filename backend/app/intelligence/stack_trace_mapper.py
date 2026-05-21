from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.intelligence.stack_trace_parser import (
    parse_stack_trace,
    ParsedTrace,
    StackFrame,
)
from app.graph.graph_memory import repository_graph_memory

logger = logging.getLogger(__name__)


@dataclass
class MappedFrame:
    frame         : StackFrame
    matched_nodes : list      = field(default_factory=list)
    graph_edges   : list      = field(default_factory=list)
    confidence    : float     = 0.0
    match_reason  : str       = ""


@dataclass
class TraceMapResult:
    parsed_trace   : ParsedTrace
    mapped_frames  : list = field(default_factory=list)
    failure_root   : object = None
    affected_nodes : list   = field(default_factory=list)
    affected_files : list   = field(default_factory=list)


class StackTraceMapper:

    def __init__(self):
        self._refresh()

    def _refresh(self):
        self._graph = repository_graph_memory.get("active_graph", {})
        self._nodes = self._graph.get("nodes", {})
        self._edges = [
            e for e in self._graph.get("edges", [])
            if e.get("source") and e.get("target")
        ]

    def map(self, error_log):
        self._refresh()
        parsed = parse_stack_trace(error_log)
        result = TraceMapResult(parsed_trace=parsed)

        if not parsed.frames:
            return result

        for frame in parsed.frames:
            mapped = self._map_frame(frame)
            result.mapped_frames.append(mapped)

        result.failure_root = self._find_failure_root(result.mapped_frames)

        seen_nodes = set()
        seen_files = set()
        for mf in result.mapped_frames:
            for n in mf.matched_nodes:
                seen_nodes.add(n)
            if mf.frame.file_path:
                seen_files.add(mf.frame.file_path)

        result.affected_nodes = sorted(seen_nodes)
        result.affected_files = sorted(seen_files)
        return result

    def to_dict(self, result):
        return {
            "language":      result.parsed_trace.language,
            "error_type":    result.parsed_trace.error_type,
            "error_message": result.parsed_trace.error_message,
            "frame_count":   len(result.parsed_trace.frames),
            "mapped_frames": [
                {
                    "file":          mf.frame.file_path,
                    "file_name":     mf.frame.file_name,
                    "line":          mf.frame.line_number,
                    "function":      mf.frame.function,
                    "matched_nodes": mf.matched_nodes,
                    "graph_edges":   mf.graph_edges[:5],
                    "confidence":    round(mf.confidence, 2),
                    "match_reason":  mf.match_reason,
                }
                for mf in result.mapped_frames
            ],
            "failure_root": (
                {
                    "file":      result.failure_root.frame.file_path,
                    "line":      result.failure_root.frame.line_number,
                    "function":  result.failure_root.frame.function,
                    "nodes":     result.failure_root.matched_nodes,
                    "confidence": round(result.failure_root.confidence, 2),
                }
                if result.failure_root else None
            ),
            "affected_nodes": result.affected_nodes,
            "affected_files": result.affected_files,
        }

    def _map_frame(self, frame):
        mapped    = MappedFrame(frame=frame)
        func_name = frame.function.lower().strip()
        file_name = frame.file_name.lower().strip()

        exact_matches = []
        file_matches  = []
        edge_matches  = []
        fuzzy_matches = []

        for node_id, node_data in self._nodes.items():
            node_lower = node_id.lower()

            if node_lower == func_name:
                exact_matches.append(node_id)
                continue

            meta      = node_data.get("metadata", {})
            meta_file = (meta.get("file_path") or meta.get("file") or "").lower()
            if meta_file and file_name in meta_file and func_name in node_lower:
                file_matches.append(node_id)
                continue

            if func_name and len(func_name) >= 3:
                if func_name in node_lower or node_lower in func_name:
                    fuzzy_matches.append(node_id)

        # Edge-based search — catches method calls stored as edges
        for edge in self._edges:
            src = (edge.get("source") or "").lower()
            tgt = (edge.get("target") or "").lower()

            if tgt.endswith(f".{func_name}") or tgt == func_name:
                matched = edge.get("source", "")
                if matched and matched not in edge_matches:
                    edge_matches.append(matched)
                continue

            if src == func_name or src.endswith(f".{func_name}"):
                matched = edge.get("source", "")
                if matched and matched not in edge_matches:
                    edge_matches.append(matched)

        if exact_matches:
            mapped.matched_nodes = exact_matches
            mapped.confidence    = 0.95
            mapped.match_reason  = "exact function name match in graph nodes"
        elif file_matches:
            mapped.matched_nodes = file_matches
            mapped.confidence    = 0.80
            mapped.match_reason  = "function + file path match in node metadata"
        elif edge_matches:
            mapped.matched_nodes = edge_matches
            mapped.confidence    = 0.75
            mapped.match_reason  = f"function '{frame.function}' found as edge target in graph"
        elif fuzzy_matches:
            mapped.matched_nodes = fuzzy_matches[:3]
            mapped.confidence    = 0.45
            mapped.match_reason  = "fuzzy function name substring match"
        else:
            mapped.matched_nodes = []
            mapped.confidence    = 0.0
            mapped.match_reason  = "no matching graph node or edge found"

        if mapped.matched_nodes:
            matched_set = set(mapped.matched_nodes)
            for edge in self._edges:
                if (edge.get("source") in matched_set or
                        edge.get("target") in matched_set):
                    mapped.graph_edges.append(edge)

        return mapped

    def _find_failure_root(self, mapped_frames):
        candidates = [m for m in mapped_frames if m.confidence >= 0.4]
        if not candidates:
            return mapped_frames[-1] if mapped_frames else None
        return candidates[-1]