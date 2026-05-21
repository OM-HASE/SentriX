from __future__ import annotations

import re
import difflib
import logging

from app.cognition.symbol_resolution_engine import SymbolResolutionEngine

logger = logging.getLogger(__name__)

# ==========================================
# LANGUAGE-AWARE STDLIB METHOD SETS
# ==========================================
# These methods are valid stdlib calls for each language.
# They must NEVER be flagged as unresolved — they are
# confirmed-valid method names for that language's runtime.

_CPP_STDLIB = {
    # std::vector
    "push_back","pop_back","push_front","pop_front","begin","end",
    "rbegin","rend","cbegin","cend","crbegin","crend",
    "size","empty","clear","resize","reserve","capacity",
    "front","back","at","insert","erase","emplace","emplace_back",
    "swap","assign","data","shrink_to_fit","max_size",
    # std::string
    "length","substr","find","rfind","replace","c_str","append",
    "compare","contains","starts_with","ends_with","npos",
    "to_string","stoi","stof","stod",
    # std::map / std::set
    "count","lower_bound","upper_bound","equal_range","key_comp",
    # std::pair
    "first","second","make_pair",
    # std::algorithm
    "sort","reverse","find_if","count_if","transform","accumulate",
    "min","max","min_element","max_element","copy","fill","unique",
    # streams
    "cout","cin","cerr","endl","flush","getline","printf","scanf",
    "peek","get","getline","read","write","open","close","is_open",
    # common
    "print","println","to_string","from_string",
}

_JAVA_STDLIB = {
    # ArrayList / List
    "add","get","set","remove","size","isEmpty","contains",
    "indexOf","lastIndexOf","clear","addAll","removeAll","retainAll",
    "toArray","iterator","listIterator","subList","sort","replaceAll",
    # HashMap / Map
    "put","containsKey","containsValue","keySet","values","entrySet",
    "getOrDefault","putIfAbsent","computeIfAbsent","forEach","merge",
    # String
    "length","charAt","substring","indexOf","contains","startsWith",
    "endsWith","trim","strip","split","toLowerCase","toUpperCase",
    "equals","equalsIgnoreCase","replace","replaceAll","matches",
    "toCharArray","valueOf","format","join","isEmpty","isBlank",
    "compareTo","compareToIgnoreCase","intern","concat","hashCode",
    # Object
    "toString","equals","hashCode","getClass","clone","notify",
    "notifyAll","wait","finalize",
    # System
    "println","print","printf","flush","exit","currentTimeMillis",
    "arraycopy","gc","getenv","getProperty",
    # Collections
    "unmodifiableList","singletonList","emptyList","nCopies","frequency",
    "shuffle","fill","copy","swap","min","max","disjoint","addAll",
    # Arrays
    "asList","stream","parallelSort","binarySearch","copyOf",
    "copyOfRange","fill","equals","deepEquals","deepToString",
    # Iterator
    "hasNext","next","remove",
}

_JAVASCRIPT_STDLIB = {
    # Array
    "push","pop","shift","unshift","splice","slice","indexOf",
    "lastIndexOf","includes","find","findIndex","filter","map",
    "reduce","reduceRight","forEach","some","every","sort","reverse",
    "join","concat","fill","flat","flatMap","entries","keys","values",
    "from","isArray","copyWithin","at",
    # String
    "charAt","charCodeAt","indexOf","lastIndexOf","includes",
    "startsWith","endsWith","substring","slice","split","trim",
    "trimStart","trimEnd","replace","replaceAll","toLowerCase",
    "toUpperCase","concat","repeat","match","search","normalize",
    "padStart","padEnd","at",
    # Object
    "keys","values","entries","assign","freeze","create","defineProperty",
    "getPrototypeOf","hasOwnProperty","toString","valueOf",
    # Promise
    "then","catch","finally","resolve","reject","all","allSettled",
    "race","any",
    # Console
    "log","error","warn","info","debug","table","dir","trace","time",
    "timeEnd","group","groupEnd","assert","clear","count",
    # Date
    "now","getTime","getDate","getMonth","getFullYear","toISOString",
    "toLocaleDateString","toLocaleTimeString","toString","valueOf",
    # Math
    "abs","ceil","floor","round","max","min","pow","sqrt","random",
    "trunc","sign","log","exp","sin","cos","tan","PI",
    # JSON
    "stringify","parse",
    # common
    "length","size","toString","toFixed","toLocaleString",
}

_PYTHON_STDLIB = {
    # list
    "append","extend","insert","remove","pop","clear","index",
    "count","sort","reverse","copy",
    # dict
    "get","keys","values","items","update","setdefault","pop",
    "popitem","clear","copy","fromkeys",
    # str
    "split","strip","lstrip","rstrip","join","lower","upper",
    "replace","find","rfind","index","rindex","startswith",
    "endswith","format","encode","decode","count","zfill",
    "ljust","rjust","center","title","capitalize","swapcase",
    "isdigit","isalpha","isalnum","isspace","isupper","islower",
    "splitlines","expandtabs","translate",
    # set
    "add","discard","difference","union","intersection","issubset",
    "issuperset","symmetric_difference","update",
    # common
    "len","range","print","type","isinstance","hasattr","getattr",
    "setattr","delattr","open","close","read","write","readline",
    "readlines","seek","tell","flush",
    # itertools / built-ins  
    "enumerate","zip","map","filter","sorted","reversed","sum",
    "min","max","abs","round","int","float","str","bool","list",
    "dict","set","tuple","bytes","bytearray",
}

_GO_STDLIB = {
    # Go doesn't have methods on builtins — append/len/cap are functions.
    # But fmt/os methods appear as method calls in the graph:
    "Println","Printf","Fprintf","Sprintf","Errorf","Scanf",
    "Print","Fprintln","Fprint",
    # os
    "Open","Create","Remove","Mkdir","Stat","Exit","Args",
    "Getenv","Setenv","Stdin","Stdout","Stderr",
    # strings
    "Contains","HasPrefix","HasSuffix","Split","Join","Replace",
    "TrimSpace","Trim","TrimLeft","TrimRight","ToLower","ToUpper",
    "Index","Count","Repeat","Title","EqualFold","Fields","Map",
    # strconv
    "Itoa","Atoi","FormatInt","ParseInt","FormatFloat","ParseFloat",
    # len/cap/append are functions, not methods — don't flag them
}

_RUST_STDLIB = {
    # Vec
    "push","pop","len","is_empty","clear","iter","iter_mut",
    "into_iter","get","first","last","contains","sort","dedup",
    "retain","extend","append","insert","remove","drain","split_at",
    "truncate","resize","with_capacity","capacity","as_slice",
    "as_mut_slice","windows","chunks","iter_mut","into_iter",
    # String/str
    "is_empty","chars","contains","starts_with","ends_with","find",
    "replace","trim","split","lines","to_string","parse","as_str",
    "as_bytes","bytes","chars","repeat","to_lowercase","to_uppercase",
    "split_whitespace","splitn","rsplitn","trim_start","trim_end",
    # HashMap
    "insert","get","remove","contains_key","len","is_empty","iter",
    "keys","values","entry","or_insert","or_default","get_mut",
    # Result/Option
    "unwrap","expect","is_ok","is_err","ok","err","map","and_then",
    "or_else","unwrap_or","unwrap_or_else","is_some","is_none",
    # println!/format! are macros, not methods
}

_CSHARP_STDLIB = {
    # List<T>
    "Add","AddRange","Remove","RemoveAt","RemoveAll","RemoveRange",
    "Clear","Contains","Count","Find","FindAll","FindIndex","Sort",
    "IndexOf","LastIndexOf","Insert","InsertRange","Reverse","ToArray",
    "AsReadOnly","Exists","TrueForAll","ForEach","GetRange","BinarySearch",
    "ConvertAll","CopyTo","Capacity","Trim","TrimExcess",
    # Dictionary
    "Add","Remove","ContainsKey","ContainsValue","TryGetValue","Keys",
    "Values","Clear","Count","TryAdd","GetValueOrDefault",
    # String
    "Length","Contains","StartsWith","EndsWith","Substring","IndexOf",
    "LastIndexOf","Replace","Trim","TrimStart","TrimEnd","Split",
    "ToLower","ToUpper","Equals","Format","Join","IsNullOrEmpty",
    "IsNullOrWhiteSpace","Concat","Copy","Compare","CompareTo",
    "PadLeft","PadRight","Remove","Insert","ToCharArray","Normalize",
    # Console
    "WriteLine","Write","ReadLine","Read","ReadKey","Clear","Beep",
    "ResetColor","SetCursorPosition",
    # LINQ (common)
    "Where","Select","OrderBy","OrderByDescending","GroupBy","First",
    "FirstOrDefault","Last","LastOrDefault","Single","Any","All",
    "Count","Sum","Min","Max","Average","ToList","ToArray","ToDictionary",
    "Skip","Take","Distinct","Union","Intersect","Except","Concat",
    # Array
    "Length","Sort","Reverse","Copy","IndexOf","BinarySearch",
    "Resize","CreateInstance","GetLength","Rank",
    # Object
    "ToString","Equals","GetHashCode","GetType","MemberwiseClone",
}

# Master lookup by language name
_STDLIB_BY_LANGUAGE: dict[str, set] = {
    "cpp":        _CPP_STDLIB,
    "c":          _CPP_STDLIB,  # C shares most
    "java":       _JAVA_STDLIB,
    "javascript": _JAVASCRIPT_STDLIB,
    "typescript": _JAVASCRIPT_STDLIB,
    "python":     _PYTHON_STDLIB,
    "go":         _GO_STDLIB,
    "rust":       _RUST_STDLIB,
    "csharp":     _CSHARP_STDLIB,
    "cs":         _CSHARP_STDLIB,
}

# Absolute baseline — always skip regardless of language
_ALWAYS_SKIP = {
    "__init__", "__str__", "__repr__", "__len__", "__iter__",
    "__next__", "__enter__", "__exit__", "__del__", "__eq__",
    "__lt__", "__gt__", "__le__", "__ge__", "__ne__", "__hash__",
    "__getitem__", "__setitem__", "__delitem__", "__contains__",
    "__add__", "__sub__", "__mul__", "__truediv__", "__mod__",
}


class SymbolicValidationEngine:

    def __init__(self, graph):
        self.graph   = graph
        self.nodes   = graph.get("nodes", {})
        self.edges   = [
            e for e in graph.get("edges", [])
            if e.get("source") and e.get("target")
        ]
        self.language        = (graph.get("language") or "unknown").lower()
        self._stdlib         = self._get_stdlib()
        self.entity_index    = self._build_entity_index()
        self.defined_symbols = self._build_defined_symbols()
        self.symbol_resolver = SymbolResolutionEngine(graph)

    # ======================================
    # STDLIB LOOKUP
    # ======================================

    def _get_stdlib(self) -> set:
        base = set(_ALWAYS_SKIP)
        lang_stdlib = _STDLIB_BY_LANGUAGE.get(self.language, set())
        base.update(lang_stdlib)
        return base

    def _is_stdlib(self, method: str) -> bool:
        return method in self._stdlib

    # ======================================
    # BUILD INDEXES
    # ======================================

    def _build_entity_index(self) -> dict:
        index = {}
        for node_id, node_data in self.nodes.items():
            meta = node_data.get("metadata", {})
            name = meta.get("entity_name")
            if name:
                index[name] = node_data
        return index

    def _build_defined_symbols(self) -> set:
        """
        Collects all named entities parsed from source by Tree-Sitter.
        These are things that ARE defined in the codebase — not bugs.
        """
        symbols = set()
        for node_id, node_data in self.nodes.items():
            node_type = node_data.get("type", "")
            meta      = node_data.get("metadata", {})
            if meta.get("synthetic"):
                continue
            if node_type in ("raw_source","repository_root",
                             "inferred_variable","calls","imports"):
                continue
            symbols.add(node_id)
            name = meta.get("entity_name")
            if name:
                symbols.add(name)
        return symbols

    # ======================================
    # MAIN VALIDATION
    # ======================================

    def validate_symbols(self) -> list:
        findings: list = []
        reported: set  = set()

        # ---- PASS 1: edge-based method resolution ----
        for edge in self.edges:
            if edge.get("relationship") != "calls":
                continue

            target = edge.get("target", "") or ""
            if not target or "." not in target:
                continue

            parts  = target.split(".")
            method = parts[-1]
            obj    = parts[-2] if len(parts) >= 2 else (edge.get("source") or "")

            if not method or len(method) < 3:
                continue

            # Skip stdlib methods for this language
            if self._is_stdlib(method):
                continue

            # Skip dunder
            if method.startswith("__"):
                continue

            # Skip pure property accesses on "self" (Python) or "this" (JS/Java)
            # These are field reads, not method calls
            if obj in ("self", "this") and len(parts) == 2:
                continue

            dedup_key = (obj, method)
            if dedup_key in reported:
                continue

            # Skip methods that ARE defined in the graph
            if method in self.defined_symbols or method in self.entity_index:
                reported.add(dedup_key)
                continue

            resolution = self.symbol_resolver.resolve_symbol(obj, method)
            if resolution.get("resolved"):
                reported.add(dedup_key)
                continue

            nearest = self._nearest(method)
            reported.add(dedup_key)

            findings.append({
                "issue_type":         "unresolved_method",
                "object":             obj,
                "method":             method,
                "symbol":             f"{obj}.{method}",
                "called_as":          target,
                "nearest_match":      nearest,
                "resolution_context": resolution,
                "repair_plan": (
                    {"suggested_symbol": nearest,
                     "repair_type": "symbol_substitution"}
                    if nearest else None
                ),
                "propagation_chain":  self._propagation_chain(method),
                "severity":           "high",
            })

        # ---- PASS 2: node-based detection (fallback) ----
        for node_id, node_data in self.nodes.items():
            if node_data.get("type") != "calls":
                continue
            meta   = node_data.get("metadata", {})
            method = meta.get("method")
            obj    = meta.get("object")
            if not method or self._is_stdlib(method):
                continue
            dedup_key = (obj, method)
            if dedup_key in reported:
                continue
            resolution = self.symbol_resolver.resolve_symbol(obj, method)
            if resolution.get("resolved"):
                continue
            if method in self.defined_symbols or method in self.entity_index:
                continue
            nearest = self._nearest(method)
            reported.add(dedup_key)
            findings.append({
                "issue_type":         "unresolved_method",
                "object":             obj,
                "method":             method,
                "symbol":             method,
                "nearest_match":      nearest,
                "resolution_context": resolution,
                "repair_plan": (
                    {"suggested_symbol": nearest, "repair_type": "symbol_substitution"}
                    if nearest else None
                ),
                "propagation_chain":  self._propagation_chain(method),
                "severity":           "high",
            })

        # ---- PASS 3: NoneType assignment detector (Python) ----
        if self.language in ("python", "unknown", ""):
            none_findings = self._detect_none_type_calls()
            for nf in none_findings:
                key = (nf.get("object"), nf.get("method"))
                if key not in reported:
                    reported.add(key)
                    findings.append(nf)

        logger.debug("SymbolicValidation[%s]: %d findings.", self.language, len(findings))
        return findings

    # ======================================
    # PASS 3: NONETYPE CALL DETECTOR
    # ======================================

    def _detect_none_type_calls(self) -> list:
        findings = []
        all_source = ""
        for node_id, node_data in self.nodes.items():
            meta = node_data.get("metadata", {})
            src  = meta.get("source_code") or meta.get("content") or ""
            if src:
                all_source += "\n" + src
        if not all_source:
            return findings

        none_assigned: set = set()
        for m in re.finditer(r'self\.(\w+)\s*=\s*None', all_source):
            none_assigned.add(m.group(1))
        if not none_assigned:
            return findings

        reported: set = set()
        for edge in self.edges:
            if edge.get("relationship") != "calls":
                continue
            source = (edge.get("source") or "").strip()
            target = (edge.get("target") or "").strip()
            if not source.startswith("self."):
                continue
            attr = source[5:]
            if attr not in none_assigned:
                continue
            if "." not in target:
                continue
            method = target.split(".")[-1]
            if self._is_stdlib(method):
                continue
            key = (attr, method)
            if key in reported:
                continue
            reported.add(key)
            findings.append({
                "issue_type":    "none_type_method_call",
                "object":        f"self.{attr}",
                "method":        method,
                "symbol":        f"self.{attr}.{method}",
                "called_as":     target,
                "none_assigned": True,
                "nearest_match": None,
                "repair_plan": {
                    "suggested_action": (
                        f"Initialize self.{attr} with a valid object "
                        f"before calling .{method}(). Current value: None"
                    ),
                    "repair_type": "null_initialization",
                },
                "propagation_chain": self._propagation_chain(f"self.{attr}.{method}"),
                "severity": "critical",
            })
        return findings

    # ======================================
    # HELPERS
    # ======================================

    def _nearest(self, symbol: str):
        candidates = list(self.defined_symbols) + list(self.entity_index.keys())
        if not candidates:
            return None
        m = difflib.get_close_matches(symbol, candidates, n=1, cutoff=0.55)
        return m[0] if m else None

    def _propagation_chain(self, symbol: str) -> list:
        return [
            {"stage": "symbol_resolution",   "state": "unresolved_symbol",    "symbol": symbol},
            {"stage": "dependency_execution", "state": "execution_instability"},
            {"stage": "runtime_execution",    "state": "runtime_failure_risk"},
        ]

    def build_entity_index(self):
        return self._build_entity_index()

    def find_closest_symbol(self, symbol):
        return self._nearest(symbol)

    def build_propagation_chain(self, symbol):
        return self._propagation_chain(symbol)