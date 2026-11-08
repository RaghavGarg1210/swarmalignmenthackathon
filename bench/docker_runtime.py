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


ROOT=Path(__file__).resolve().parents[1]
CHESS_SOCKET_DIR='/run/chess-submission'


def chess_names(run):
    agents,_=container_names(run)
    suffix=agents[len('swarm-agents-'):]
    return f'swarm-grader-{suffix}',f'swarm-chess-sock-{suffix}'


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


def _start_chess_grader(root):
    """Grader container + shared socket volume for the Chess Decision Challenge.

    The grader holds the answer key and the gateway code; the agents' container
    only shares the volume that contains the Unix socket. A named volume keeps
    the socket inside Docker's VM, so this also works with Docker Desktop.
    """
    grader,volume=chess_names(root)
    _start(['docker','volume','create','--label','swarm-integrity.role=chess-socket',volume])
    # A fresh named volume is root-owned; hand it to the unprivileged run user.
    _start(['docker','run','--rm','--network','none','--user','0','-v',f'{volume}:/v',IMAGE,
            'chown',f'{os.getuid()}:{os.getgid()}','/v'])
    _start(['docker','run','-d','--network','none','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges',
            '--tmpfs','/tmp:rw,noexec,nosuid,size=64m',
            '--user',f'{os.getuid()}:{os.getgid()}',
            '-e','PYTHONDONTWRITEBYTECODE=1','-e','HOME=/tmp','-e','PYTHONPATH=/grader',
            '--name',grader,'--label','swarm-integrity.role=grader',
            '--pids-limit','128','--memory','512m','--cpus','1',
            '-v',f'{ROOT / "bench"}:/grader/bench:ro',
            '-v',f'{root / "operator" / "chess_answer_key.json"}:/grader/key.json:ro',
            '-v',f'{root / "operator" / "chess_gateway"}:/grader/state:rw',
            '-v',f'{volume}:{CHESS_SOCKET_DIR}',
            IMAGE,'python','-m','bench.chess_gateway','--socket',f'{CHESS_SOCKET_DIR}/sock',
            '--key','/grader/key.json','--state','/grader/state'])
    return grader,volume


def _wait_for_socket(container,timeout=30):
    import time
    for _ in range(timeout*2):
        r=subprocess.run(['docker','exec',container,'test','-S',f'{CHESS_SOCKET_DIR}/sock'],capture_output=True)
        if r.returncode==0:return
        time.sleep(0.5)
    raise RuntimeError('chess submission gateway did not start (no socket); see `docker logs` for the grader container')


def start_run_containers(run,chess=False):
    """Keep agent code and private operator results in separate offline containers.

    The host runner retains the API key and evaluator. The agent container mounts
    only the workspace; the results viewer mounts the whole run read-only.
    Both remain visible in Docker Desktop after the trial for inspection.
    """
    root=Path(run).resolve()
    agents,results=container_names(root)
    cpus,memory=_limits()
    extra=[]
    if chess:
        grader,volume=_start_chess_grader(root)
        extra=['-v',f'{volume}:{CHESS_SOCKET_DIR}']
    common=['docker','run','-d','--network','none','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges',
            '--tmpfs','/tmp:rw,noexec,nosuid,size=256m',
            '--user',f'{os.getuid()}:{os.getgid()}',
            '-e','PYTHONDONTWRITEBYTECODE=1','-e','HOME=/tmp']
    _start(common+['--name',agents,'--label','swarm-integrity.role=agents',
                   '--pids-limit','512','--memory',memory,'--cpus',cpus,
                   '-v',f'{root / "workspace"}:/workspace:rw','-w','/workspace',*extra,
                   IMAGE,'sleep','infinity'])
    try:
        _start(common+['--name',results,'--label','swarm-integrity.role=results',
                       '--pids-limit','64','--memory','256m','--cpus','0.5',
                       '-v',f'{root}:/results:ro','-w','/results',
                       IMAGE,'tail','-n','+1','-F',
                       '/results/operator/events.jsonl',
                       '/results/operator/reasoning.jsonl'])
        if chess:
            _wait_for_socket(agents)
    except Exception:
        subprocess.run(['docker','rm','-f',agents,results]+([grader] if chess else []),capture_output=True)
        raise
    out={'agents':agents,'results':results}
    if chess:
        out.update(grader=grader,chess_socket_volume=volume)
    return out
