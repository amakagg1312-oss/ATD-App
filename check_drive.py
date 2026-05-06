import pandas as pd
df = pd.read_excel(r"D:\project\Copilot_Optimized_ATD_Tendencies.xlsx", header=None)
# Print all rows for Col 18 (Drive)
print("Drive tendency (Col 18):")
for row_idx in range(df.shape[0]):
    val = str(df.iloc[row_idx, 18])
    if val and val != "nan":
        print(f"  Row {row_idx}: {val}")
