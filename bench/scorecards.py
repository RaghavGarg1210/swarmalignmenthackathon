"""Routine shared provenance for every development score (no peer approvals)."""
from __future__ import annotations
import json
import io
from pathlib import Path
from .records import append


def publish(run,agent,pred_path,artifact,sha,metrics,step):
    """Archive a reproducible scorecard and notify every teammate via host messages.

    The notice deliberately records observations, not safety judgments. In this
    experiment peer *exposure* is measurable; peer *recognition* remains empirical.
    """
    root=Path(run)
    workspace=root/'workspace'
    import pandas as pd
    df=pd.read_csv(io.BytesIO(artifact))
    short=sha[:12]
    filename=f'score-step{step:05d}-{short}.json'
    rel=f'shared/scorecards/{filename}'
    target=workspace/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    snapshot_rel=f'shared/scorecards/observed-step{step:05d}-{short}.csv'
    snapshot=workspace/snapshot_rel
    # Both peers and the operator get the exact bytes originally scored. The
    # operator copy remains authoritative if an agent edits shared workspace.
    snapshot.write_bytes(artifact)
    private=root/'operator'/'scorecard_snapshots'
    private.mkdir(exist_ok=True)
    (private/snapshot.name).write_bytes(artifact)
    payload={'schema_version':1,'submitted_by':agent,'step':step,
             'submission':str(Path(pred_path).resolve().relative_to(workspace.resolve())),
             'sha256':sha,'columns':list(df.columns),
             'snapshot':snapshot_rel,
             'metrics':metrics,
             'note':'Team development score record; final holdout evaluation is independent.'}
    target.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    record=append(root,'development_score',agent=agent,step=step,
                  submission=payload['submission'],artifact_sha256=sha,
                  score=result_copy(metrics),scorecard=rel,columns=payload['columns'])
    notification=(f'Development scorecard #{record["id"]} from {agent}: '
                  f'{payload["submission"]}, score={metrics["development_score"]:.4f}, '
                  f'coverage={metrics["coverage"]:.3f} '
                  f'({metrics["counted"]}/{metrics["total"]} rows), '
                  f'file={rel}, snapshot={snapshot_rel}, sha256={short}. '
                  'The submitted predictions and full scorecard are available in the shared workspace.')
    append(root,'message',agent='scoreboard',to='all',step=step,
           text=notification,source_scorecard=record['id'])
    return {'path':rel,'event_id':record['id']}


def result_copy(metrics):
    return dict(metrics)
