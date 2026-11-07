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


def _limits(want_cpus=8,want_mem_bytes=6*1024**3):
    """Cap container limits to what the Docker engine has (e.g. Docker Desktop's VM),
    otherwise `docker run --cpus 8` fails on smaller machines."""
    info=subprocess.run(['docker','info','--format','{{.NCPU}} {{.MemTotal}}'],capture_output=True,text=True)
    try:
        ncpu,mem=(int(x) for x in info.stdout.split())
    except ValueError:
        return str(want_cpus),'6g'
    cpus=max(1,min(want_cpus,ncpu))
    mem_bytes=max(512*1024**2,min(want_mem_bytes,int(mem*0.75)))
    return str(cpus),f'{mem_bytes//1024**2}m'


def start_run_containers(run):
    """Keep agent code and private operator results in separate offline containers.

    The host runner retains the API key and evaluator. The agent container mounts
    only the workspace; the results viewer mounts the whole run read-only.
    Both remain visible in Docker Desktop after the trial for inspection.
    """
    root=Path(run).resolve()
    agents,results=container_names(root)
    cpus,memory=_limits()
    common=['docker','run','-d','--network','none','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges',
            '--tmpfs','/tmp:rw,noexec,nosuid,size=256m',
            '--user',f'{os.getuid()}:{os.getgid()}',
            '-e','PYTHONDONTWRITEBYTECODE=1','-e','HOME=/tmp']
    _start(common+['--name',agents,'--label','swarm-integrity.role=agents',
                   '--pids-limit','512','--memory',memory,'--cpus',cpus,
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
