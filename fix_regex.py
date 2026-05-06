with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the regex patterns - in raw strings:
# \\ = 2 chars in source = 1 literal backslash in regex = matches \ in input
# \\\\ = 4 chars in source = 2 literal backslashes in regex = matches \\ in input

# The input has \\sqrt (2 literal backslashes), so pattern needs \\\\sqrt (4 in source)
# But \\s for whitespace needs just \\s in raw string (2 in source = 1 in regex = whitespace)

old_patterns = [
    # Wrong: \\\\s matches literal \s, should be \\s for whitespace
    (r'latex = re.sub(r"\\\\sqrt\\s*\\{([^}]+)\\}", r"sqrt(\\1)", latex)',
     r'latex = re.sub(r"\\\\sqrt\s*\\{([^}]+)\\}", r"sqrt(\\1)", latex)'),
    (r'latex = re.sub(r"(\\\\frac\\s*\\{[^}]+\\}\\s*\\{[^}]+\\})\\s*(\\()", r"\\1*\\2", latex)',
     r'latex = re.sub(r"(\\\\frac\s*\\{[^}]+\\}\s*\\{[^}]+\\})\s*(\\()", r"\\1*\\2", latex)'),
    (r'latex = re.sub(rf"\\\\{func}\\s*\\(?", f"{func}(", latex)',
     r'latex = re.sub(rf"\\\\{func}\s*\\(?", f"{func}(", latex)'),
]

for old, new in old_patterns:
    content = content.replace(old, new)

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed regex whitespace patterns")
