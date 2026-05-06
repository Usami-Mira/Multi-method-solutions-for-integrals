with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add sqrt handling after the \\frac while loop, before power handling
insert_marker = "s = re.sub(r'{([^{}]+)}^{([^{}]+)}', r'\\1**\\2', s)"
insert_point = content.find(insert_marker)

if insert_point != -1:
    sqrt_code = """    # Handle \\\\sqrt{expr} -> (expr)**(1/2) before brace removal
    while True:
        idx = s.find(r'\\\\sqrt')
        if idx == -1:
            break
        brace_start = s.find('{', idx)
        if brace_start == -1:
            break
        depth, i = 0, brace_start
        while i < len(s):
            if s[i] == '{':
                depth += 1
            elif s[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            break
        inner = s[brace_start+1:i]
        s = s[:idx] + f'({inner})**(1/2)' + s[i+1:]
    
"""
    content = content[:insert_point] + sqrt_code + content[insert_point:]
    
    with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added sqrt handling to _simple_latex_to_sympy_str")
else:
    print("Could not find insertion point")
