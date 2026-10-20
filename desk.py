import sqlite3
from datetime import datetime,timezone
PRIORITIES=('low','normal','high','urgent')
TRANSITIONS={'open':('triaged',),'triaged':('in_progress','open'),'in_progress':('resolved','triaged'),'resolved':('closed','open'),'closed':()}
def connection(path):
 c=sqlite3.connect(path,timeout=10);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.executescript("""
 CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL,priority TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY,ticket_id INTEGER NOT NULL REFERENCES tickets(id),event TEXT NOT NULL,at TEXT NOT NULL);
 """);return c

def text(x,label,maximum):
 if not isinstance(x,str) or not x.strip() or len(x)>maximum:raise ValueError(f'{label} requires 1–{maximum} characters')
 if any(ord(c)<32 and c not in '\n\t' for c in x):raise ValueError('Control characters not allowed')
 return x.strip()
def priority(p):
 if p not in PRIORITIES:raise ValueError('Invalid priority')
 return p
def now():return datetime.now(timezone.utc).isoformat()
def create(c,title,description,p='normal'):
 title=text(title,'Title',120);description=text(description,'Description',3000);priority(p);at=now()
 with c:
  cur=c.execute('INSERT INTO tickets(title,description,priority,status,created_at,updated_at) VALUES(?,?,?,?,?,?)',(title,description,p,'open',at,at));i=cur.lastrowid
  c.execute('INSERT INTO history(ticket_id,event,at) VALUES(?,?,?)',(i,'Created',at))
 return get(c,i)
def get(c,i):
 row=c.execute('SELECT * FROM tickets WHERE id=?',(i,)).fetchone()
 if row is None:raise LookupError('Ticket not found')
 obj=dict(row);obj['history']=[dict(x) for x in c.execute('SELECT event,at FROM history WHERE ticket_id=? ORDER BY id',(i,))];return obj
def listing(c,q='',status='all'):
 if not isinstance(q,str) or len(q)>120:raise ValueError('Search is too long')
 if status!='all' and status not in TRANSITIONS:raise ValueError('Invalid status')
 # Escape LIKE metacharacters: search is literal rather than wildcard input.
 like='%'+q.replace('!','!!').replace('%','!%').replace('_','!_')+'%'
 return [dict(x) for x in c.execute("SELECT * FROM tickets WHERE (title LIKE ? ESCAPE '!' OR description LIKE ? ESCAPE '!') AND (?='all' OR status=?) ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,id DESC",(like,like,status,status))]

def update(c,i,*,title=None,description=None,p=None,status=None):
 # Explicit write lock means transitions are checked against the latest state.
 try:
  c.execute('BEGIN IMMEDIATE');old=get(c,i);new=dict(old);events=[]
  for key,value,maxlen in [('title',title,120),('description',description,3000)]:
   if value is not None:new[key]=text(value,key.capitalize(),maxlen)
  if p is not None:new['priority']=priority(p)
  if status is not None:
   if status not in TRANSITIONS[old['status']]:raise ValueError('Transition not allowed')
   new['status']=status;events.append(f"Status: {old['status']} → {status}")
  if any(new[k]!=old[k] for k in ('title','description','priority')):events.append('Details updated')
  if not events:raise ValueError('No changes supplied')
  at=now();c.execute('UPDATE tickets SET title=?,description=?,priority=?,status=?,updated_at=? WHERE id=?',(new['title'],new['description'],new['priority'],new['status'],at,i))
  c.executemany('INSERT INTO history(ticket_id,event,at) VALUES(?,?,?)',[(i,e,at) for e in events]);c.commit();return get(c,i)
 except Exception:c.rollback();raise
