"""Adaption Responses API client, with zero third-party runtime dependencies."""
from __future__ import annotations
import os,re,json,time,random,http.client,urllib.request,urllib.error

BASE='https://api.prod.adaptionlabs.ai/api/v1'
RETRY_HTTP={408,409,425,429,500,502,503,504}


class EmptyResponse(RuntimeError):
    """The provider answered but produced no output text (e.g. the output cap was
    reached during reasoning). The call was still billed, so usage is attached."""
    def __init__(self,message,usage=None):
        super().__init__(message)
        self.usage=usage or {}


class Adaption:
    def __init__(self,base=None,timeout=None,attempts=None):
        self.base=(base or os.getenv('ADAPTION_BASE_URL') or BASE).rstrip('/')
        self.key=os.getenv('ADAPTION_API_KEY')
        # Long reasoning responses can take minutes; a short socket timeout would
        # abort a request that is still generating.
        self.timeout=float(timeout or os.getenv('ADAPTION_TIMEOUT_SECONDS') or 300)
        self.attempts=int(attempts or os.getenv('ADAPTION_ATTEMPTS') or 4)
        if not self.key: raise RuntimeError('Set ADAPTION_API_KEY in host environment; never share it with agents.')

    def _request(self,method,path,payload=None):
        headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'}
        data=json.dumps(payload).encode() if payload is not None else None
        last=None
        for attempt in range(self.attempts):
            req=urllib.request.Request(self.base+path,data=data,headers=headers,method=method)
            try:
                with urllib.request.urlopen(req,timeout=self.timeout) as response:
                    return json.loads(response.read().decode())
            except urllib.error.HTTPError as e:
                msg=e.read(700).decode(errors='replace')
                last=RuntimeError(f'Adaption API HTTP {e.code}: {msg}')
                if e.code not in RETRY_HTTP: raise last from e
            except (urllib.error.URLError,TimeoutError,ConnectionError,
                    http.client.HTTPException,json.JSONDecodeError) as e:
                # Timeouts, resets and truncated bodies are transient: retry them.
                last=RuntimeError(f'Adaption API transport error: {type(e).__name__}: {e}')
            if attempt<self.attempts-1:
                time.sleep(min(30,2**attempt)+random.random())
        raise last

    def models(self): return self._request('GET','/models?type=hosted')

    def answer(self,model,system,prompt,max_output=65536,reasoning=None):
        """Return (text, usage, reasoning_text).

        `reasoning` is an optional Responses-API reasoning object, e.g.
        {'effort':'high','summary':'detailed'}; omitted when None.
        """
        payload={'model':model,'instructions':system,'input':[
            {'role':'user','content':prompt}], 'max_output_tokens':max_output,
            'store':False, 'agentic_memory':False}
        if reasoning: payload['reasoning']=reasoning
        result=self._request('POST','/responses',payload)
        text,thoughts=split_output(result)
        usage=result.get('usage',{}) or {}
        if not text.strip():
            raise EmptyResponse(f'No output_text in response (status={result.get("status")})',usage)
        return text,usage,thoughts


THINK=re.compile(r'<think(?:ing)?>(.*?)</think(?:ing)?>',re.S|re.I)


def split_output(result):
    """Separate the visible answer from any chain of thought in a response.

    Handles Responses-API `reasoning` items (summary_text and reasoning_text
    parts), message parts typed as reasoning/thinking, a `reasoning_content`
    field, and <think>...</think> blocks inlined in the answer text. Encrypted
    reasoning cannot be read and is ignored.
    """
    texts,thoughts=[],[]
    for item in result.get('output',[]) or []:
        kind=item.get('type')
        if kind=='reasoning':
            for part in (item.get('summary') or [])+(item.get('content') or []):
                if isinstance(part,dict) and part.get('text'): thoughts.append(part['text'])
            if isinstance(item.get('text'),str): thoughts.append(item['text'])
        elif kind=='message':
            if isinstance(item.get('reasoning_content'),str): thoughts.append(item['reasoning_content'])
            for part in item.get('content',[]) or []:
                ptype=part.get('type')
                if ptype=='output_text': texts.append(part.get('text',''))
                elif ptype in ('reasoning','reasoning_text','thinking') and part.get('text'):
                    thoughts.append(part['text'])
    if isinstance(result.get('reasoning_content'),str): thoughts.append(result['reasoning_content'])
    text='\n'.join(texts)
    inline=THINK.findall(text)
    if inline:
        thoughts.extend(t.strip() for t in inline)
        text=THINK.sub('',text)
    return text,'\n\n'.join(t for t in thoughts if t and t.strip())


def probe(client,model,max_output=2000):
    """Try reasoning settings on a tiny prompt; report what comes back."""
    variants=[('default',None),('summary_detailed',{'summary':'detailed'}),
              ('effort_high_summary_detailed',{'effort':'high','summary':'detailed'})]
    prompt='Is 391 prime? Think it through, then answer with one JSON object: {"prime": true|false}.'
    out=[]
    for name,reasoning in variants:
        payload={'model':model,'instructions':'Answer briefly.','input':[{'role':'user','content':prompt}],
                 'max_output_tokens':max_output,'store':False,'agentic_memory':False}
        if reasoning: payload['reasoning']=reasoning
        try:
            raw=client._request('POST','/responses',payload)
        except Exception as exc:
            out.append({'variant':name,'accepted':False,'error':str(exc)[:300]});continue
        text,thoughts=split_output(raw)
        usage=raw.get('usage') or {}
        out.append({'variant':name,'accepted':True,'status':raw.get('status'),
                    'output_item_types':[i.get('type') for i in raw.get('output',[]) or []],
                    'reasoning_tokens':(usage.get('output_tokens_details') or {}).get('reasoning_tokens'),
                    'reasoning_chars_captured':len(thoughts),
                    'reasoning_preview':thoughts[:300],'answer':text[:200],'cost':usage.get('cost'),
                    'raw':raw})
    return out
