import sys
sys.path.insert(0, "D:/PHY-LLM/MMSI/src")
from calc_solver.tools.latex_parser import best_parse

test_cases = [
    (r"\sin x + C", "x"),
    (r"\frac{2}{3}(x - 2)\sqrt{x + 1} + C", "x"),
    (r"2\sin(\sqrt{x}) + C", "x"),
    (r"7\tan x - \sec x + C", "x"),
    (r"x + \frac{1}{2x^2} + C", "x"),
    (r"\int \frac{1}{\sec x} dx", "x"),  # Though this is integral notation
]

print("Testing new SymPy native parser:")
for expr, var in test_cases:
    result = best_parse(expr, var)
    status = "?" if result is not None else "?"
    print(f"{status} {expr[:45]:45s} ¡ú {result}")
