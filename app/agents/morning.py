import needle
from app.mcp.client import call
@needle.tool
def tasks(): """Get open tasks.""";return call('tasks_list',status='open')
@needle.tool
def blogs(): """Get interesting blog posts.""";return call('blog_interesting',limit=10)
@needle.tool
def people(): """Get interesting network candidates.""";return call('opportunity_interesting',limit=10)
def run(prompt='Prepare my morning briefing.'):
 a=needle.Needle(tools=[tasks,blogs,people],system='You are Morning Briefing Needle. Produce a compact action-oriented briefing from tasks, technical reading and network opportunities.');return a.complete(prompt)
