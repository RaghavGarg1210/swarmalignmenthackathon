"""Create a downloadable, self-contained archive of a completed run."""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import zipfile


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]


def archive_run(run: str | Path) -> Path:
    """Zip every saved run file, with message/tool indexes beside the raw logs."""
    root = Path(run).resolve()
    if not (root / 'operator' / 'events.jsonl').exists():
        raise FileNotFoundError(f'No event log found under {root}')
    export_dir = (root.parent.parent if root.parent.name == 'runs' else root.parent) / 'exports'
    export_dir.mkdir(parents=True, exist_ok=True)
    destination = export_dir / f'{root.name}-complete-record.zip'
    temporary = destination.with_suffix('.zip.tmp')

    events = _jsonl(root / 'operator' / 'events.jsonl')
    messages = [event for event in events if event.get('kind') == 'message']
    actions = [event for event in events if event.get('kind') == 'action']
    reports = _jsonl(root / 'operator' / 'reports.jsonl')
    run_started = next((event for event in events if event.get('kind') == 'run_started'), {})
    run_completed = next((event for event in reversed(events) if event.get('kind') == 'run_completed'), {})
    stats = {
        'run_id': root.name,
        'started_utc': run_started.get('when'),
        'ended_utc': run_completed.get('when'),
        'arm': run_started.get('arm'),
        'agents': run_started.get('roles'),
        'agent_models': run_started.get('agent_models'),
        'event_counts': dict(Counter(event.get('kind') for event in events)),
        'actions_by_agent': dict(Counter(event.get('agent') for event in actions)),
        'reporting_agents': [report.get('agent') for report in reports],
        'official_grades': [event for event in events if event.get('kind') == 'chess_official_grade'],
        'completion': run_completed,
    }
    board = [
        '# Recorded team messageboard',
        '',
        'Extracted from operator/events.jsonl. The raw event log is authoritative.',
    ]
    for message in messages:
        sender = message.get('agent', 'unknown')
        label = ('OPERATOR SIMULATED' if message.get('simulated') else
                 'GRADING SERVICE' if sender == 'grading_service' else 'LIVE AGENT')
        board.extend([
            '',
            f"## {message.get('when')} — {sender} → {message.get('to')} [{label}]",
            f"Event ID: `{message.get('id')}`; step: `{message.get('step')}`.",
            '',
            message.get('text', ''),
        ])

    source_root = Path(__file__).resolve().parents[1]
    source_files = sorted((source_root / 'bench').glob('*.py'))
    source_files += [path for path in (source_root / 'README.md', source_root / 'Dockerfile') if path.exists()]
    manifest = []
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr('README.md',
            f'Complete saved record for {root.name}.\n\n'
            'raw_run/ contains every file present in the run directory when this archive was created.\n'
            'derived/messageboard.md and messageboard.jsonl contain every recorded board message.\n'
            'derived/tool_calls.jsonl contains every recorded tool action with arguments and results.\n'
            'derived/stats.json summarizes participation, scores, reports, and budget.\n'
            'context/source/ records the runner source and prompt definitions at archive time.\n'
            'operator/reasoning.jsonl contains only reasoning returned by the model provider; '
            'unreturned private reasoning is unavailable. Synthetic operator continuations '
            'are under operator/peer_seed_gemma/ and are not authentic agent reasoning.\n')
        for path in sorted(root.rglob('*')):
            if path.is_file():
                name = 'raw_run/' + path.relative_to(root).as_posix()
                data = path.read_bytes()
                archive.writestr(name, data)
                manifest.append(f'{sha256(data).hexdigest()}  {name}')
        archive.writestr('derived/messageboard.md', '\n'.join(board) + '\n')
        archive.writestr('derived/messageboard.jsonl', ''.join(json.dumps(item, ensure_ascii=False) + '\n' for item in messages))
        archive.writestr('derived/tool_calls.jsonl', ''.join(json.dumps(item, ensure_ascii=False) + '\n' for item in actions))
        archive.writestr('derived/stats.json', json.dumps(stats, indent=2, ensure_ascii=False) + '\n')
        for path in source_files:
            name = 'context/source/' + path.relative_to(source_root).as_posix()
            data = path.read_bytes()
            archive.writestr(name, data)
            manifest.append(f'{sha256(data).hexdigest()}  {name}')
        archive.writestr('sha256-manifest.txt', '\n'.join(manifest) + '\n')
    with zipfile.ZipFile(temporary) as archive:
        bad_file = archive.testzip()
        if bad_file is not None:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f'Archive validation failed at {bad_file}')
    temporary.replace(destination)
    return destination
