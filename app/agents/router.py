from app.agents import task,blog,opportunity,research,github,morning

def route(t):
 l=t.lower().strip()
 if l=='/tasks':return task.list_open_tasks()
 if l.startswith('/done '):
  try:return task.complete_task(int(l[6:].strip()))
  except:return {'error':'Usage: /done <id>'}
 if l=='/blogs':return blog.run('Fetch new posts, curate them, and show interesting ones.')
 if l=='/people':return opportunity.run('Show the most interesting imported network profiles.')
 if l=='/morning':return morning.run()
 if any(x in l for x in ['github','pull request','repository','repo']):return github.run(t)
 if any(x in l for x in ['blog','industry news','company news']):return blog.run(t)
 if any(x in l for x in ['linkedin','profile','network','person to talk']):return opportunity.run(t)
 if any(x in l for x in ['research','paper','arxiv','look up']):return research.run(t)
 return task.run(t)
