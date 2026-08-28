import json
from pathlib import Path
from datetime import datetime
import feedparser,httpx
from mcp.server.fastmcp import FastMCP
from app import state
from app.config import settings
mcp=FastMCP("needle-daily-v2")
@mcp.tool()
def tasks_create(title:str,notes:str='',due_at:str|None=None)->dict:
 """Create a personal task."""
 i=state.create_task(title,notes,due_at);return state.get_task(i)
@mcp.tool()
def tasks_list(status:str='open')->list[dict]: """List personal tasks.""";return state.list_tasks(status)
@mcp.tool()
def tasks_complete(task_id:int)->dict: """Complete a personal task.""";return state.complete_task(task_id) or {'error':'Task not found'}
@mcp.tool()
def reminders_schedule(task_id:int,remind_at:str)->dict:
 """Schedule an ISO-8601 reminder."""
 datetime.fromisoformat(remind_at)
 if not state.get_task(task_id): return {'error':'Task not found'}
 i=state.add_reminder(task_id,remind_at);return {'id':i,'task_id':task_id,'remind_at':remind_at}
@mcp.tool()
def blog_fetch_new(limit_per_source:int=20)->list[dict]:
 """Fetch recent posts from configured RSS/Atom feeds."""
 out=[]
 for s in json.loads(Path('/app/data/sources.json').read_text()):
  f=feedparser.parse(s['feed'])
  for e in f.entries[:limit_per_source]:
   if e.get('link'):
    a={'source':s['name'],'url':e.link,'title':e.get('title',''),'published_at':e.get('published',''),'description':e.get('summary','')};state.upsert_article(a);out.append(a)
 return out
@mcp.tool()
def blog_candidates(limit:int=50)->list[dict]: """Get unscored blog candidates.""";return state.candidates(limit)
@mcp.tool()
def blog_save_score(url:str,score:float,interesting:bool,summary:str)->dict: """Save article relevance and summary.""";state.score_article(url,max(0,min(1,score)),interesting,summary);return {'ok':True}
@mcp.tool()
def blog_interesting(limit:int=20)->list[dict]: """Get curated interesting articles.""";return state.interesting_articles(limit)
@mcp.tool()
def research_fetch_url(url:str)->dict:
 """Fetch readable public web content, using Jina Reader when configured."""
 target=('https://r.jina.ai/'+url) if settings.jina_api_key else url;h={'Authorization':'Bearer '+settings.jina_api_key} if settings.jina_api_key else {};r=httpx.get(target,headers=h,timeout=30,follow_redirects=True);r.raise_for_status();return {'url':url,'content':r.text[:50000]}
@mcp.tool()
def opportunity_import_profiles(profiles:list[dict])->dict:
 """Import approved/user-provided network profile records; no LinkedIn scraping."""
 n=0
 for p in profiles:
  if p.get('profile_url') and p.get('name'):state.import_person(p);n+=1
 return {'imported':n}
@mcp.tool()
def opportunity_candidates(limit:int=50)->list[dict]: """Get unscored network profiles.""";return state.people_candidates(limit)
@mcp.tool()
def opportunity_save_score(profile_url:str,score:float,interesting:bool,reason:str,conversation_hook:str)->dict: """Save network opportunity score.""";state.score_person(profile_url,max(0,min(1,score)),interesting,reason,conversation_hook);return {'ok':True}
@mcp.tool()
def opportunity_interesting(limit:int=20)->list[dict]: """Get high-value network candidates.""";return state.interesting_people(limit)
if __name__=='__main__':mcp.run(transport='streamable-http')
