import ollama
import json
import re
from datetime import datetime
from app.services.context_compressor import compress_context
from app.rag.retriever import retrieve_relevant_chunks


def analyze_root_cause(
    error_log,
    source_code
):

    combined_query = f"""
ERROR LOG:
{error_log}

SOURCE CODE:
{source_code}
"""

    retrieved_context = retrieve_relevant_chunks(
        combined_query,
        top_k=8
    )

    context_documents = [item["document"] for item in retrieved_context]

    combined_context = compress_context(context_documents)

    MAX_CONTEXT_CHARS = 4000
    if len(combined_context) > MAX_CONTEXT_CHARS:
        combined_context = combined_context[:MAX_CONTEXT_CHARS]

    prompt = f"""
You are an elite autonomous software debugging
and root cause analysis AI.

Your task is to perform deep technical RCA
using:
- runtime logs
- source code
- semantic repository context

You must:
- identify the exact technical issue
- analyze failure propagation
- identify impacted modules/files
- determine repair strategy
- assess risks and impact
- generate validation blueprint

ERROR LOG:
{error_log}

SOURCE CODE:
{source_code}

REPOSITORY CONTEXT:
{combined_context}

IMPORTANT RULES:
- Return ONLY valid JSON
- Do NOT include markdown
- Do NOT include comments
- Do NOT include explanations outside JSON
- Confidence score must be between 0 and 1

Return this exact JSON structure:

{{
  "incident_metadata": {{
    "id": "",
    "timestamp": "",
    "severity_level": "",
    "environment_context": {{
      "runtime": "",
      "version": "",
      "os": ""
    }}
  }},
  "diagnostic_summary": {{
    "detected_error_type": "",
    "confidence_score": 0.0,
    "brief_description": "",
    "failure_chain": [
      "",
      ""
    ]
  }},
  "root_cause_details": {{
    "primary_technical_cause": "",
    "contributing_factors": [
      "",
      ""
    ],
    "logic_violation": ""
  }},
  "code_mapping": {{
    "affected_files": [
      {{
        "file_path": "",
        "vulnerable_lines": [],
        "context_snippet": "",
        "local_variables_at_failure": {{}}
      }}
    ]
  }},
  "repair_directives": {{
    "suggested_fix_strategy": "",
    "breaking_change_risk": "",
    "required_dependencies": []
  }},
  "impact_assessment": {{
    "module_scope": "",
    "system_stability": "",
    "data_integrity_risk": ""
  }},
  "validation_blueprint": {{
    "reproduction_steps": [
      "",
      ""
    ],
    "expected_output": "",
    "assertion_criteria": ""
  }}
}}
"""

    stream  = ollama.chat(
        model="qwen2.5-coder:7b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        stream=True,
        format="json"
    )

    full_response = ""
    for chunk in stream:
        content = chunk["message"]["content"]
        full_response += content

    content = full_response

    # Remove markdown wrappers
    content = content.replace(
        "```json",
        ""
    ).replace(
        "```",
        ""
    ).strip()

    # Remove JS-style comments
    content = re.sub(
        r"//.*",
        "",
        content
    )

    # Remove trailing commas before } or ]
    content = re.sub(
        r",\s*([}\]])",
        r"\1",
        content
    )

    try:

        parsed_json = json.loads(content)

        if not parsed_json["incident_metadata"]["timestamp"]:
            parsed_json["incident_metadata"]["timestamp"] = (
                datetime.utcnow().isoformat()
            )

        if not parsed_json["incident_metadata"]["id"]:
            parsed_json["incident_metadata"]["id"] = (
                f"INC-{int(datetime.utcnow().timestamp())}"
            )

        return parsed_json

    except Exception as e:

        return {
            "error": "Failed to parse RCA JSON",
            "exception": str(e),
            "raw_response": content
        }