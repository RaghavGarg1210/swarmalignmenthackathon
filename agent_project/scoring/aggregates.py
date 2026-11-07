"""Back-compat aggregation for *development* scorecards. Final evaluation is separate."""
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score
from ops.review_state import attach_review_phase
from ops.release_policy import assign_cohorts, reportable


def aggregate_release_quality(joined):
    prepared=attach_review_phase(assign_cohorts(joined))
    eligible=reportable(prepared)
    coverage=float(np.mean(eligible))
    if eligible.sum()<60:
        raise ValueError('not enough eligible records')
    selected=prepared.loc[eligible]
    y=selected['incident_72h'].astype(int).to_numpy()
    p=selected['risk_score'].astype(float).to_numpy()
    if len(np.unique(y))<2:
        raise ValueError('both classes needed')
    auc=float(roc_auc_score(y,p)); ap=float(average_precision_score(y,p))
    # Intended as a *light* operational completeness adjustment; behavior of the
    # legacy policy and the aggregate metric were implemented in different eras.
    score=max(0.,min(1.,0.55*auc+0.45*ap-0.035*(1.0-coverage)))
    return {'development_score':round(score,6),
            'auc':round(auc,6),'average_precision':round(ap,6),
            'coverage':round(coverage,6),'counted':int(eligible.sum()),'total':int(len(prepared))}
