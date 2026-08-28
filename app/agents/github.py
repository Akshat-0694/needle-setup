import needle,subprocess
@needle.tool
def gh_read(command:str):
 """Run a restricted read-only gh command."""
 allowed=('repo view','pr list','pr view','issue list','issue view','run list','run view')
 if not command.startswith(allowed):return {'error':'Only read-only gh commands are allowed.'}
 p=subprocess.run(['gh',*command.split()],capture_output=True,text=True,timeout=30);return {'returncode':p.returncode,'stdout':p.stdout[:20000],'stderr':p.stderr[:5000]}
def run(prompt):
 a=needle.Needle(tools=[gh_read],system='You are GitHub Needle. Perform read-only GitHub inspection. Never write, merge, push, comment, or delete.');return a.complete(prompt)
