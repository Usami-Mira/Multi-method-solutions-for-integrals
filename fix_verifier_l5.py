with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/verifier.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace the L5 JSON parsing section
old_code = """            import json
            data = json.loads(raw)
            is_eq = data.get("equivalent", False)
            reason = data.get("reason", "")[:100]"""

new_code = """            import json
            # Robust JSON parsing for LLM response
            try:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    # Try to extract dict from nested structure
                    if isinstance(data, list) and len(data) > 0:
                        data = data[0] if isinstance(data[0], dict) else {}
                    else:
                        data = {}
            except (json.JSONDecodeError, TypeError):
                data = {}
            # Safe key access with fallback
            is_eq = data.get("equivalent", data.get("is_eq", data.get("equal", False)))
            reason = str(data.get("reason", data.get("explanation", "")))[:100]"""

content = content.replace(old_code, new_code)

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/verifier.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed verifier.py L5 JSON parsing")
