import pandas as pd
df = pd.read_excel(r"D:\project\Copilot_Optimized_ATD_Tendencies.xlsx", header=None)

# Search for "driving" or "layup" in any cell
for col_idx in range(df.shape[1]):
    for row_idx in range(df.shape[0]):
        val = str(df.iloc[row_idx, col_idx])
        if "driving" in val.lower() or "layup" in val.lower():
            print(f"Row {row_idx}, Col {col_idx}: {val[:150]}")
            print("---")
