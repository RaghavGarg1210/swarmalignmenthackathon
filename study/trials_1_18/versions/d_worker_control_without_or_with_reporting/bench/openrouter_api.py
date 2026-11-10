"""OpenRouter chat-completions client for mixed-model swarm runs."""
from __future__ import annotations

import json
import os
import random
import re
import time
import urllib.error
import urllib.request

from .api import EmptyResponse, RETRY_HTTP, THINK


class OpenRouter:
    def __init__(self, base=None, timeout=None, attempts=None):
        self.base=(base or os.getenv('OPENROUTER_BASE_URL') or
                   'https://openrouter.ai/api/v1').rstrip('/')
        self.key=os.getenv('OPENROUTER_API_KEY')
        self.timeout=float(timeout or os.getenv('OPENROUTER_TIMEOUT_SECONDS') or 300)
        self.attempts=int(attempts or os.getenv('OPENROUTER_ATTEMPTS') or 4)
        if not self.key:
            raise RuntimeError('Set OPENROUTER_API_KEY in the host environment; never share it with agents.')

    def _request(self, path, payload):
        headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'}
        data=json.dumps(payload).encode('utf8')
        last=None
        for attempt in range(self.attempts):
            req=urllib.request.Request(self.base+path,data=data,headers=headers,method='POST')
            try:
                with urllib.request.urlopen(req,timeout=self.timeout) as response:
                    return json.loads(response.read().decode('utf8'))
            except urllib.error.HTTPError as exc:
                detail=exc.read(700).decode(errors='replace')
                last=RuntimeError(f'OpenRouter API HTTP {exc.code}: {detail}')
                if exc.code not in RETRY_HTTP:
                    raise last from exc
            except (urllib.error.URLError,TimeoutError,ConnectionError,json.JSONDecodeError) as exc:
                last=RuntimeError(f'OpenRouter transport error: {type(exc).__name__}: {exc}')
            if attempt<self.attempts-1:
                time.sleep(min(30,2**attempt)+random.random())
        raise last

    def answer(self, model, system, prompt, max_output=16384, reasoning=None):
        payload={'model':model,
                 'messages':[{'role':'system','content':system},
                             {'role':'user','content':prompt}],
                 'max_tokens':max_output,
                 'include_reasoning':True,
                 'usage':{'include':True}}
        if reasoning:
            payload['reasoning']=reasoning
        result=self._request('/chat/completions',payload)
        choices=result.get('choices') or []
        message=(choices[0].get('message') or {}) if choices else {}
        content=message.get('content') or ''
        if isinstance(content,list):
            content='\n'.join(str(part.get('text','')) for part in content
                              if isinstance(part,dict) and part.get('type') in ('text','output_text'))
        thoughts=[]
        if isinstance(message.get('reasoning'),str):
            thoughts.append(message['reasoning'])
        for part in message.get('reasoning_details') or []:
            if isinstance(part,dict) and isinstance(part.get('text'),str):
                thoughts.append(part['text'])
        inline=THINK.findall(content)
        if inline:
            thoughts.extend(t.strip() for t in inline)
            content=THINK.sub('',content)
        usage=normalize_usage(result.get('usage') or {})
        if not content.strip():
            raise EmptyResponse('No output text in OpenRouter response',usage,'\n\n'.join(thoughts))
        return content,usage,'\n\n'.join(t for t in thoughts if t and t.strip())


def normalize_usage(raw):
    """Match the token and cost fields consumed by the existing runner."""
    prompt_tokens=raw.get('prompt_tokens',raw.get('input_tokens')) or 0
    completion_tokens=raw.get('completion_tokens',raw.get('output_tokens')) or 0
    prompt_details=raw.get('prompt_tokens_details') or raw.get('input_tokens_details') or {}
    completion_details=raw.get('completion_tokens_details') or raw.get('output_tokens_details') or {}
    usage={'input_tokens':prompt_tokens,'output_tokens':completion_tokens,
           'total_tokens':raw.get('total_tokens',prompt_tokens+completion_tokens),
           'input_tokens_details':{'cached_tokens':prompt_details.get('cached_tokens') or 0},
           'output_tokens_details':{'reasoning_tokens':completion_details.get('reasoning_tokens') or 0}}
    if isinstance(raw.get('cost'),(float,int)):
        usage['cost']=raw['cost']
    return usage
