"""Submission contract validation, independent of scoring semantics."""
import numpy as np
import pandas as pd

def validate_predictions(df, expected_ids):
    if 'row_id' not in df or 'risk_score' not in df:
        raise ValueError('must include row_id,risk_score')
    if df['row_id'].duplicated().any():
        raise ValueError('duplicate row_id values')
    if set(df.row_id.astype(str))!=set(expected_ids.astype(str)):
        raise ValueError('missing or unexpected row_id values')
    score=pd.to_numeric(df.risk_score,errors='raise')
    if not np.isfinite(score).all() or not score.between(0,1).all():
        raise ValueError('risk_score must be finite and within [0,1]')
    return True
