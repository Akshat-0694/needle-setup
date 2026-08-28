import asyncio
from mcp import Client
URL='http://mcp:9000/mcp'
async def _call(name,args):
 async with Client(URL) as c:
  r=await c.call_tool(name,args)
  if r.is_error: raise RuntimeError(str(r.content))
  if r.structured_content is not None:return r.structured_content
  return '\n'.join(getattr(x,'text',str(x)) for x in r.content)
def call(name,**args): return asyncio.run(_call(name,args))
