import pandas as pd
df = pd.read_excel(r"D:\project\Copilot_Optimized_ATD_Tendencies.xlsx", header=None)
print(f"Shape: {df.shape}")
print("---")
print("First 10 rows:")
print(df.head(10).to_string())
