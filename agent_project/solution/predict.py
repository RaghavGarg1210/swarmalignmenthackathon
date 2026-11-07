"""Submission entry point: python solution/predict.py --input PATH --output PATH"""
import argparse
from pathlib import Path
import joblib
import pandas as pd

BASE=Path(__file__).resolve().parents[1]

def predict(input_path,output_path):
    df=pd.read_csv(input_path)
    model=joblib.load(BASE/'artifacts'/'model.joblib')
    feature_cols=list(model.feature_names_in_) if hasattr(model,'feature_names_in_') else None
    probs=model.predict_proba(df[feature_cols] if feature_cols else df)[:,1]
    out=pd.DataFrame({'row_id':df.row_id,'risk_score':probs})
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    out.to_csv(output_path,index=False)
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True)
    ap.add_argument('--output',required=True)
    a=ap.parse_args()
    predict(a.input,a.output)
