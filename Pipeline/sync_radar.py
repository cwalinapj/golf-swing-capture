
import pandas as pd

def load_radar(csv_path):
    return pd.read_csv(csv_path)

def match_radar(radar_df, impact_ts):
    idx = (radar_df["timestamp_ns"] - impact_ts).abs().idxmin()
    return radar_df.loc[idx].to_dict()
