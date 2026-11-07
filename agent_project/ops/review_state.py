"""Shared review-state normalization used by historical release pipelines."""
from __future__ import annotations
import pandas as pd

# A legacy scorecard used this vocabulary to distinguish rows sent to manual review.
REVIEW_PHASES={'NONE':0,'CHECK':1,'QUEUE':2,'MANUAL_REVIEW':2}

def attach_review_phase(frame):
    out=frame.copy()
    col=out['review_code'] if 'review_code' in out else pd.Series(['NONE']*len(out),index=out.index)
    out['_review_phase']=col.fillna('NONE').astype(str).str.upper().map(REVIEW_PHASES).fillna(0).astype(int)
    return out
