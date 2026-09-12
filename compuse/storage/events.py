"""Durable tamper-evident event storage."""
from __future__ import annotations
import hashlib, json, sqlite3
from pathlib import Path
_ZERO_HASH="0"*64
class EventStore:
    def __init__(self,path=":memory:"):
        self.path=str(path)
        if self.path!=":memory:": Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,check_same_thread=False,timeout=10); self.db.row_factory=sqlite3.Row
        for pragma in ("PRAGMA foreign_keys=ON","PRAGMA busy_timeout=10000","PRAGMA synchronous=FULL"): self.db.execute(pragma)
        if self.path!=":memory:": self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (run_id TEXT NOT NULL, seq INTEGER NOT NULL, type TEXT NOT NULL, payload TEXT NOT NULL, timestamp TEXT NOT NULL, previous_event_hash TEXT NOT NULL, event_hash TEXT NOT NULL, PRIMARY KEY(run_id,seq), UNIQUE(event_hash))"); self.db.commit()
    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
    @staticmethod
    def _hash(prev,run_id,seq,typ,body,timestamp): return hashlib.sha256(f"{prev}|{run_id}|{seq}|{typ}|{body}|{timestamp}".encode()).hexdigest()
    def append(self,run_id,event_type,payload,timestamp):
        if not run_id or not event_type or not timestamp: raise ValueError("event identity is required")
        body=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row=self.db.execute("SELECT seq,event_hash FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1",(run_id,)).fetchone(); seq=row["seq"]+1 if row else 1; prev=row["event_hash"] if row else _ZERO_HASH; h=self._hash(prev,run_id,seq,event_type,body,timestamp)
            self.db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?)",(run_id,seq,event_type,body,timestamp,prev,h))
        return seq
    def verify(self,run_id):
        prev=_ZERO_HASH
        try:
            for row in self.db.execute("SELECT * FROM events WHERE run_id=? ORDER BY seq",(run_id,)):
                h=self._hash(prev,row["run_id"],row["seq"],row["type"],row["payload"],row["timestamp"])
                if row["previous_event_hash"]!=prev or row["event_hash"]!=h:return False
                prev=h
        except (sqlite3.DatabaseError,TypeError): return False
        return True
    def events(self,run_id): return self.db.execute("SELECT * FROM events WHERE run_id=? ORDER BY seq",(run_id,))
