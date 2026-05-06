import re

with open("src/calc_solver/agents/base.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add agent_name parameter to _call method signature
content = re.sub(
    r"(async def _call\(\s+self,\s+system: str,\s+user: str,\s+json_mode: bool = False,\s+temperature: Optional\[float\] = None,)\s*\) -> str:",
    r"\1\n        agent_name: str = \"unknown\",\n    ) -> str:",
    content
)

# Add agent_name parameter to _call_messages method signature  
content = re.sub(
    r"(async def _call_messages\(\s+self,\s+messages: list\[dict\],\s+json_mode: bool = False,\s+temperature: Optional\[float\] = None,)\s*\) -> str:",
    r"\1\n        agent_name: str = \"unknown\",\n    ) -> str:",
    content
)

# Add agent_name to client.chat calls in _call method
content = re.sub(
    r"(return await self\.client\.chat\(\s+messages,\s+temperature=temperature if temperature is not None else self\.temperature,\s+json_mode=json_mode,)\s*\)",
    r"\1\n            agent_name=agent_name,\n        )",
    content
)

with open("src/calc_solver/agents/base.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed")
