import needle
from app.mcp.client import call
@needle.tool
def fetch_new(): """Fetch configured industry blog feeds.""";return call('blog_fetch_new')
@needle.tool
def candidates(limit:int=50): """Get unscored blog candidates.""";return call('blog_candidates',limit=limit)
@needle.tool
def save_score(url:str,score:float,interesting:bool,summary:str): """Save article score and summary.""";return call('blog_save_score',url=url,score=score,interesting=interesting,summary=summary)
def run(prompt):
 a=needle.Needle(tools=[fetch_new,candidates,save_score],system='You are Blog Curator Needle. Find and rank high-signal technical posts about AI systems, CUDA/GPU, inference, ML infrastructure, agents, compilers, distributed systems and open source. Ignore generic marketing. Score 0..1 and summarize interesting posts.');return a.complete(prompt)
