with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the _simple_latex_to_sympy_str function and add sqrt handling before brace removal
new_sqrt_handling = """    # Handle \\sqrt{expr} -> (expr)**(1/2) before brace removal
    while True:
        idx = s.find(r'\\\\sqrt')
        if idx == -1:
            break
        # Find the opening brace
        brace_start = s.find('{', idx)
        if brace_start == -1:
            break
        # Find matching closing brace
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
        # Extract and convert
        inner = s[brace_start+1:i]
        s = s[:idx] + f'({inner})**(1/2)' + s[i+1:]
    
    # Handle \\sin{expr} -> sin(expr), etc.
    for func in ['sin', 'cos', 'tan', 'sec', 'csc', 'cot', 'log', 'ln', 'exp']:
        while True:
            idx = s.find(r'\\\\' + func)
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
            s = s[:idx] + f'{func}({inner})' + s[i+1:]
    
    s = re.sub(r'\\{([^{}]+)\\}\\^\\{([^{}]+)\\}', r'\\1**\\2', s)
    s = re.sub(r'([a-zA-Z])\\^\\{([^}]+)\\}', r'\\1**\\2', s)
    s = re.sub(r'([a-zA-Z])\\^([a-zA-Z0-9]+)', r'\\1**\\2', s)
    s = s.replace(r'\\\\cdot', '*').replace(r'\\\\times', '*')
    # Remove remaining LaTeX commands but preserve math function names
    math_funcs = ['sin', 'cos', 'tan', 'sec', 'csc', 'cot', 'log', 'ln', 'exp', 'sqrt', 'abs', 'floor', 'ceil']
    for func in math_funcs:
        s = s.replace(r'\\\\' + func, func)
    s = re.sub(r'\\\\[a-zA-Z]+', '', s)
    s = s.replace('{', '').replace('}', '')"""

# Find the section to replace (from \\frac handling to brace removal)
start_marker = "s = s.replace(r'\\\\\\\\cdot', '*').replace(r'\\\\\\\\times', '*')"
end_marker = "s = s.replace('{', '').replace('}', '')"

start_idx = end_idx = None
for i, line in enumerate(lines):
    if start_marker in line:
        start_idx = i
    elif end_marker in line and start_idx is not None:
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    # Replace the section
    new_lines = lines[:start_idx+1] + [new_sqrt_handling + '\n'] + lines[end_idx+1:]
    with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Added sqrt/function handling to _simple_latex_to_sympy_str")
else:
    print(f"Could not find markers: start={start_idx}, end={end_idx}")
