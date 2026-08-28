import needle
from app.mcp.client import call
@needle.tool
def candidates(limit:int=50): """Get imported unscored network profiles.""";return call('opportunity_candidates',limit=limit)
@needle.tool
def save_score(profile_url:str,score:float,interesting:bool,reason:str,conversation_hook:str): """Save profile score and conversation hook.""";return call('opportunity_save_score',profile_url=profile_url,score=score,interesting=interesting,reason=reason,conversation_hook=conversation_hook)
def run(prompt):
 a=needle.Needle(tools=[candidates,save_score],system='You are Opportunity Needle. Rank approved/imported network profiles for genuine professional conversations. Favor technical depth, strong evidence of building/research/open source, relevance to AI/ML systems/CUDA/GPU/inference, trajectory and a concrete conversation hook. Do not infer private facts or automate outreach. Score 0..1.');return a.complete(prompt)
