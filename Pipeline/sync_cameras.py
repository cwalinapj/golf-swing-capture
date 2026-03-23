import pandas as pd

def map_roof_to_mono(roof_df, mono_df):
    mapping = []

    for _, row in roof_df.iterrows():
        ts = row["timestamp_ns"]

        idx = (mono_df["timestamp_ns"] - ts).abs().idxmin()
        mono_frame = mono_df.loc[idx]

        mapping.append({
            "roof_frame": int(row["frame_idx"]),
            "mono_frame": int(mono_frame["frame_idx"]),
        })

    return mapping
