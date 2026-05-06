with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/verifier.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix: replace the broken _load() call with proper get() usage
old = """            from calc_solver.llm.prompts import get, format_prompt
            prompts = _load()
            system = get("equivalence_judge", "system") if prompts.get("equivalence_judge", {}).get("system") else """""

new = """            from calc_solver.llm.prompts import get, format_prompt
            try:
                system = get("equivalence_judge", "system")
            except (KeyError, TypeError):
                system = """""

content = content.replace(old, new)

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/verifier.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed verifier.py _load issue")
