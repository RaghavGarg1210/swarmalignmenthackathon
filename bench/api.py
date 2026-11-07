"""Adaption Responses API client, with zero third-party runtime dependencies."""
from __future__ import annotations
import os,json,time,urllib.request,urllib.error

BASE='https://api.prod.adaptionlabs.ai/api/v1'

class Adaption:
    def __init__(self,base=None):
        self.base=(base or os.getenv('ADAPTION_BASE_URL') or BASE).rstrip('/')
        self.key=os.getenv('ADAPTION_API_KEY')
        if not self.key: raise RuntimeError('Set ADAPTION_API_KEY in host environment; never share it with agents.')
    def _request(self,method,path,payload=None):
        headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'}
        data=json.dumps(payload).encode() if payload is not None else None
        req=urllib.request.Request(self.base+path,data=data,headers=headers,method=method)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req,timeout=110) as response:
                    return json.loads(response.read().decode())
            except urllib.error.HTTPError as e:
                if e.code in (429,502,503,504) and attempt<2:
                    time.sleep(2**attempt)
                    continue
                msg=e.read(700).decode(errors='replace')
                raise RuntimeError(f'Adaption API HTTP {e.code}: {msg}') from e
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
        if not texts:
            raise RuntimeError(f'No output_text in response (status={result.get("status")})')
        usage=result.get('usage',{})
        return '\n'.join(texts),usage
