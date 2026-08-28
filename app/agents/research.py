import needle
from app.mcp.client import call
@needle.tool
def fetch_url(url:str): """Fetch public URL text.""";return call('research_fetch_url',url=url)
def run(prompt):
 a=needle.Needle(tools=[fetch_url],system='You are Research Needle. Use primary sources and technical evidence. Clearly distinguish evidence from inference.');return a.complete(prompt)
