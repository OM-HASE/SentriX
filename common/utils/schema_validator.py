import json
from jsonschema import validate, ValidationError

def validate_schema(data: dict, schema: dict):
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Schema validation failed: {e.message}")
