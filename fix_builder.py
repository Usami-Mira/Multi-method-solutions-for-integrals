with open("src/calc_solver/agents/builder.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add _extract_integrand function at module level (after imports, before class)
new_func = """

def _extract_integrand(question: str, var: str) -> str:
    """Extract the integrand expression from a calculus problem question string."""
    import re
    # Simple pattern: find content between \int and d<var>
    # Handle LaTeX: \int <expr> d<var>
    pattern = r"\\\\int\\s+(.+?)\\s+d" + re.escape(var)
    match = re.search(pattern, question)
    if match:
        return match.group(1).strip()
    # Fallback: return the question itself (let parser handle it)
    return question
"""

# Find position after imports (after last import line)
lines = content.split("\n")
insert_pos = 0
for i, line in enumerate(lines):
    if line.startswith("from ") or line.startswith("import "):
        insert_pos = i + 1
    elif line.strip() and not line.startswith("#") and not line.startswith("from ") and not line.startswith("import "):
        if insert_pos > 0:
            break

# Insert the function
lines.insert(insert_pos, new_func)

with open("src/calc_solver/agents/builder.py", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Fixed")
