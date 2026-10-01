
import pandas as pd

# Load JSON
df = pd.read_json("datasets/transactions.json")

# Inspect columns
print(df.columns)

# Save as CSV
df.to_csv("outputs/results/Test/01/transactions.csv", index=False)

