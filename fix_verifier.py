import re

with open('D:/PHY-LLM/MMSI/src/calc_solver/tools/verifier.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'equivalence_judge' in line and 'prompts = _load()' in line:
        indent = '            '
        lines[i] = indent + 'prompts = _load()\n'
        lines.insert(i+1, indent + 'system = get("equivalence_judge", "system") if prompts.get("equivalence_judge", {}).get("system") else ""\n')
        break

with open('D:/PHY-LLM/MMSI/src/calc_solver/tools/verifier.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed')
