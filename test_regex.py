import re

test_cases = [
    r"2\sin\left(\sqrt{x}\right) + C",
    r"x + \frac{1}{2x^2} + C",
    r"7\tan x - \sec x + C",
    r"sin(x) + C",
]

pattern = r"\s*[+\-]\s*C\b"

for tc in test_cases:
    result = re.sub(pattern, "", tc, flags=re.IGNORECASE).strip()
    print(f"Input:  {tc}")
    print(f"Output: {result}")
    print()
