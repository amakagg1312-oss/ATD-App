import pandas as pd
df = pd.read_excel(r"D:\project\Copilot_Optimized_ATD_Tendencies.xlsx", header=None)

# Print all column headers (row 0)
print("Tendency names (Row 0):")
for col_idx in range(df.shape[1]):
    val = str(df.iloc[0, col_idx])
    if val and val != "nan":
        print(f"  Col {col_idx}: {val}")
