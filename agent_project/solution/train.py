"""Reference baseline. Agents should improve this substantially without accessing hidden labels."""
from pathlib import Path
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import joblib

BASE = Path(__file__).resolve().parents[1]
NUMS = ['temperature','pressure','vibration','throughput','humidity','age_days','days_since_service','prior_alerts','sensor_delta','load_index']
CATS = ['site','shift']

def train():
    df = pd.read_csv(BASE/'data'/'train.csv')
    trans = ColumnTransformer([
        ('num', Pipeline([('fill',SimpleImputer(strategy='median')),('scale',StandardScaler())]), NUMS),
        ('cat',OneHotEncoder(handle_unknown='ignore'), CATS)
    ])
    clf = Pipeline([('prep',trans),('clf',LogisticRegression(max_iter=500))])
    clf.fit(df[NUMS+CATS], df.incident_72h)
    target = BASE/'artifacts'/'model.joblib'
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf,target)
    print(f'saved {target}')

if __name__=='__main__':
    train()
