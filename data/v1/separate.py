import os

import pandas as pd

sim_rows = []
unsim_rows = []
df = pd.read_excel('./reprocessed_sim.xlsx')

if len(df.index) > 0:
    for i, row in df.iterrows():
        if row['bearing_similarity'] >= 0.85:
            sim_rows.append(row)
        else:
            unsim_rows.append(row)

df = pd.DataFrame(sim_rows)
df.to_excel(f'./processed_sim_final.xlsx', sheet_name='unprocessed', index=False)

df = pd.DataFrame(unsim_rows)
df.to_excel(f'./unprocessed_sim_final.xlsx', sheet_name='unprocessed', index=False)

