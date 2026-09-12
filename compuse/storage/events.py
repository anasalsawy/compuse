import sqlite3,json,hashlib
class EventStore:
 def __init__(self,path=":memory:"):
  self.db=sqlite3.connect(path); self.db.row_factory=sqlite3.Row; self.db.execute("PRAGMA journal_mode=WAL"); self.db.execute("PRAGMA synchronous=FULL"); self.db.execute("CREATE TABLE IF NOT EXISTS events(run_id TEXT,seq INTEGER,type TEXT,payload TEXT,timestamp TEXT,previous_event_hash TEXT,event_hash TEXT,PRIMARY KEY(run_id,seq))"); self.db.commit()
 def append(self,run_id,typ,payload,timestamp):
  with self.db:
   r=self.db.execute("SELECT * FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1",(run_id,)).fetchone(); seq=(r['seq']+1 if r else 1); prev=(r['event_hash'] if r else '0'*64); body=json.dumps(payload,sort_keys=True,separators=(',',':')); h=hashlib.sha256(f'{prev}|{run_id}|{seq}|{typ}|{body}|{timestamp}'.encode()).hexdigest(); self.db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',(run_id,seq,typ,body,timestamp,prev,h))
 def verify(self,run_id):
  prev='0'*64
  for r in self.db.execute('SELECT * FROM events WHERE run_id=? ORDER BY seq',(run_id,)):
   h=hashlib.sha256(f"{prev}|{r['run_id']}|{r['seq']}|{r['type']}|{r['payload']}|{r['timestamp']}".encode()).hexdigest()
   if r['previous_event_hash']!=prev or r['event_hash']!=h:return False
   prev=h
  return True
