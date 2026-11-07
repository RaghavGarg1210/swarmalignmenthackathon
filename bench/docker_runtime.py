"""Persistent Docker containers for a visible four-agent trial."""
from __future__ import annotations
import hashlib,os,re,subprocess
from pathlib import Path

IMAGE='swarm-integrity:local'


def container_names(run):
    root=Path(run).resolve()
    slug=re.sub(r'[^a-z0-9-]+','-',root.name.lower()).strip('-')[:26] or 'run'
    suffix=hashlib.sha256(str(root).encode()).hexdigest()[:8]
    return f'swarm-agents-{slug}-{suffix}',f'swarm-results-{slug}-{suffix}'


def _start(command):
    result=subprocess.run(command,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('Docker container start failed: '+result.stderr[-1000:])


def start_run_containers(run):
    """Keep agent code and private operator results in separate offline containers.

    The host runner retains the API key and evaluator. The agent container mounts
    only the workspace; the results viewer mounts the whole run read-only.
    Both remain visible in Docker Desktop after the trial for inspection.
    """
    root=Path(run).resolve()
    agents,results=container_names(root)
    common=['docker','run','-d','--network','none','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges',
            '--tmpfs','/tmp:rw,noexec,nosuid,size=256m',
            '--user',f'{os.getuid()}:{os.getgid()}',
            '-e','PYTHONDONTWRITEBYTECODE=1','-e','HOME=/tmp']
    _start(common+['--name',agents,'--label','swarm-integrity.role=agents',
                   '--pids-limit','512','--memory','6g','--cpus','8',
                   '-v',f'{root / "workspace"}:/workspace:rw','-w','/workspace',
                   IMAGE,'sleep','infinity'])
    try:
        _start(common+['--name',results,'--label','swarm-integrity.role=results',
                       '--pids-limit','64','--memory','256m','--cpus','0.5',
                       '-v',f'{root}:/results:ro','-w','/results',
                       IMAGE,'sleep','infinity'])
    except Exception:
        subprocess.run(['docker','rm','-f',agents],capture_output=True)
        raise
    return {'agents':agents,'results':results}
