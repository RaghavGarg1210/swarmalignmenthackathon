"""Adaption Responses API client, with zero third-party runtime dependencies."""
from __future__ import annotations
import os,json,time,random,http.client,urllib.request,urllib.error

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

    def answer(self,model,system,prompt,max_output=65536):
        payload={'model':model,'instructions':system,'input':[
            {'role':'user','content':prompt}], 'max_output_tokens':max_output,
            'store':False, 'agentic_memory':False}
        result=self._request('POST','/responses',payload)
        texts=[]
        for item in result.get('output',[]):
            if item.get('type')=='message':
                for part in item.get('content',[]):
                    if part.get('type')=='output_text': texts.append(part.get('text',''))
        usage=result.get('usage',{}) or {}
        if not ''.join(texts).strip():
            raise EmptyResponse(f'No output_text in response (status={result.get("status")})',usage)
        return '\n'.join(texts),usage
