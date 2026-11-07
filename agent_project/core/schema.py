"""Schemas shared by data and release instrumentation."""
ID_COLUMN='row_id'
PREDICTION_COLUMN='risk_score'
OPTIONAL_AUDIT_FIELDS=('review_code','review_note','cohort')
ALLOWED_REVIEW_CODES=('NONE','CHECK','QUEUE','MANUAL_REVIEW')
