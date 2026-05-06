import re

with open("src/calc_solver/agents/builder.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add _extract_integrand function before _self_check
func_code = '''

def _extract_integrand(question: str, var: str) -> str:
    """Extract the integrand expression from a calculus problem question string."""
    # Pattern: \int <integrand> dx or \int <integrand> d<var>
    pattern = rf"\\\\int\\s+([^\\$]+?)\\s+d\\{var}\\b"
    match = re.search(pattern, question)
    if match:
        return match.group(1).strip()
    # Fallback pattern
    pattern2 = rf"\\\\int\\s+(.+?)\\s+d[a-zA-Z]+"
    match2 = re.search(pattern2, question)
    if match2:
        return match2.group(1).strip()
    return ""

'''

marker = "    def _self_check(self, result: dict, problem: Problem)"
if marker in content and "_extract_integrand" not in content:
    content = content.replace(marker, func_code + marker)
    with open("src/calc_solver/agents/builder.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added _extract_integrand")
else:
    print("Already exists or not found")
