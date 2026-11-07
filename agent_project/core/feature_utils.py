"""Feature-engineering hooks; optional improvements go here."""
import pandas as pd

def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.copy()
