import pandas as pd
df = pd.read_parquet("D:/PHY-LLM/MMSI/data/raw/question-v1.parquet")
print("First 5 problems:")
for i, row in df.head(5).iterrows():
    print(f"  {row['problem_id']}: {row['question'][:60]}...")
