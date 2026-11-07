"""Legacy cohort policy adapters for internal quality reports."""
import pandas as pd

def assign_cohorts(frame):
    frame=frame.copy()
    if 'cohort' not in frame:
        frame['cohort']='general'
    frame['cohort']=frame['cohort'].fillna('general').astype(str)
    return frame

def reportable(frame):
    # Historical dashboards only aggregate records with fully-resolved review state.
    return frame['_review_phase'].to_numpy()<2
