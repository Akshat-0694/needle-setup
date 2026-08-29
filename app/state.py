from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import datetime
from zoneinfo import ZoneInfo
import os,sqlite3,json
from app.config import settings
os.makedirs(settings.data_dir,exist_ok=True)
DB=os.path.join(settings.data_dir,"needle.db")
db=sqlite3.connect(DB,check_same_thread=False); db.row_factory=sqlite3.Row
db.executescript('''
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',due_at TEXT,status TEXT NOT NULL DEFAULT 'open',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,completed_at TEXT);
CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT,task_id INTEGER NOT NULL,remind_at TEXT NOT NULL,sent INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT NOT NULL,actor TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS articles(id INTEGER PRIMARY KEY AUTOINCREMENT,source TEXT NOT NULL,url TEXT UNIQUE NOT NULL,title TEXT NOT NULL,published_at TEXT,description TEXT,score REAL,interesting INTEGER DEFAULT 0,summary TEXT,seen INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS people(id INTEGER PRIMARY KEY AUTOINCREMENT,source TEXT NOT NULL,profile_url TEXT UNIQUE NOT NULL,name TEXT NOT NULL,headline TEXT,profile_json TEXT NOT NULL,score REAL,interesting INTEGER DEFAULT 0,reason TEXT,conversation_hook TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
''');db.commit()
def create_task(title,notes='',due_at=None):
 c=db.execute('INSERT INTO tasks(title,notes,due_at) VALUES(?,?,?)',(title,notes,due_at));db.commit();return c.lastrowid
def get_task(i):
 r=db.execute('SELECT * FROM tasks WHERE id=?',(i,)).fetchone();return dict(r) if r else None
def list_tasks(status='open'):
 rows=db.execute('SELECT * FROM tasks '+('WHERE status=? ' if status!='all' else '')+'ORDER BY id DESC',((status,) if status!='all' else ())).fetchall();return [dict(r) for r in rows]
def complete_task(i):
 db.execute("UPDATE tasks SET status='completed',completed_at=CURRENT_TIMESTAMP WHERE id=?",(i,));db.commit();return get_task(i)
def add_reminder(task_id,when):
 c=db.execute('INSERT INTO reminders(task_id,remind_at) VALUES(?,?)',(task_id,when));db.commit();return c.lastrowid
def due_reminders(now):
 return [dict(r) for r in db.execute('SELECT r.*,t.title FROM reminders r JOIN tasks t ON t.id=r.task_id WHERE r.sent=0 AND r.remind_at<=? ORDER BY r.id',(now,)).fetchall()]
def mark_sent(i): db.execute('UPDATE reminders SET sent=1 WHERE id=?',(i,));db.commit()
def add_event(t,a,p): db.execute('INSERT INTO events(event_type,actor,payload) VALUES(?,?,?)',(t,a,json.dumps(p,default=str)));db.commit()
def upsert_article(a):
 db.execute('INSERT INTO articles(source,url,title,published_at,description) VALUES(?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET title=excluded.title,published_at=excluded.published_at,description=excluded.description',tuple(a.get(k) for k in ['source','url','title','published_at','description']));db.commit()
def candidates(n=50): return [dict(r) for r in db.execute('SELECT * FROM articles WHERE score IS NULL ORDER BY id DESC LIMIT ?',(n,)).fetchall()]
def score_article(url,score,interesting,summary): db.execute('UPDATE articles SET score=?,interesting=?,summary=?,seen=1 WHERE url=?',(score,int(interesting),summary,url));db.commit()
def interesting_articles(n=20): return [dict(r) for r in db.execute('SELECT * FROM articles WHERE interesting=1 ORDER BY score DESC LIMIT ?',(n,)).fetchall()]
def import_person(p):
 db.execute('INSERT INTO people(source,profile_url,name,headline,profile_json) VALUES(?,?,?,?,?) ON CONFLICT(profile_url) DO UPDATE SET name=excluded.name,headline=excluded.headline,profile_json=excluded.profile_json',(p.get('source','import'),p['profile_url'],p['name'],p.get('headline',''),json.dumps(p,ensure_ascii=False)));db.commit()
def people_candidates(n=50): return [dict(r) for r in db.execute('SELECT * FROM people WHERE score IS NULL ORDER BY id DESC LIMIT ?',(n,)).fetchall()]
def score_person(url,score,interesting,reason,hook): db.execute('UPDATE people SET score=?,interesting=?,reason=?,conversation_hook=? WHERE profile_url=?',(score,int(interesting),reason,hook,url));db.commit()
def interesting_people(n=20): return [dict(r) for r in db.execute('SELECT * FROM people WHERE interesting=1 ORDER BY score DESC LIMIT ?',(n,)).fetchall()]


def unnotified_interesting_articles(n=20):
    rows = db.execute(
        '''
        SELECT *
        FROM articles
        WHERE interesting=1
          AND notified=0
        ORDER BY score DESC, id DESC
        LIMIT ?
        ''',
        (n,),
    ).fetchall()

    return [dict(r) for r in rows]


def mark_articles_notified(urls):
    if not urls:
        return

    now = datetime.now(
        ZoneInfo(settings.timezone)
    ).isoformat()

    db.executemany(
        '''
        UPDATE articles
        SET notified=1,
            notified_at=?
        WHERE url=?
        ''',
        [(now, url) for url in urls],
    )

    db.commit()


# --- Research paper persistence ---
# V2 additive layer. Existing task/article/person/GitHub
# persistence remains unchanged.

db.execute("""
CREATE TABLE IF NOT EXISTS research_papers(
    arxiv_id TEXT PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    authors TEXT DEFAULT '',
    abstract TEXT DEFAULT '',
    published_at TEXT,
    updated_at TEXT,
    categories TEXT DEFAULT '',
    source TEXT DEFAULT 'arxiv',

    deterministic_score REAL DEFAULT 0,
    needle_score REAL DEFAULT 0,
    score REAL DEFAULT 0,

    interesting INTEGER DEFAULT 0,
    researched INTEGER DEFAULT 0,

    reason TEXT DEFAULT '',
    technical_area TEXT DEFAULT '',
    implementation_url TEXT,

    notified INTEGER DEFAULT 0,
    notified_at TEXT,

    notion_page_id TEXT,
    notion_url TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()


def upsert_research_paper(item):
    """
    Insert or update an arXiv research paper.

    IMPORTANT:
    This function matches the existing research_papers schema.
    Structured fields such as authors/categories/signals are
    serialized before crossing the SQLite boundary.
    """

    arxiv_id = item.get(
        "arxiv_id",
        item.get("id", ""),
    )

    url = item.get("url")

    if not url and arxiv_id:
        url = (
            "https://arxiv.org/abs/"
            + str(arxiv_id)
        )

    authors = item.get("authors", [])

    if isinstance(authors, (list, tuple, set)):
        authors = json.dumps(
            list(authors),
            ensure_ascii=False,
            default=str,
        )
    else:
        authors = str(authors or "")

    categories = item.get("categories", [])

    if isinstance(categories, (list, tuple, set)):
        categories = json.dumps(
            list(categories),
            ensure_ascii=False,
            default=str,
        )
    else:
        categories = str(categories or "")

    # The existing schema does not have a signals column.
    # Store the deterministic signals alongside the reason.
    signals = item.get("signals", [])

    if isinstance(signals, (list, tuple, set)):
        signals_text = ", ".join(
            str(x) for x in signals
        )
    else:
        signals_text = str(signals or "")

    reason = str(
        item.get("reason", "")
        or ""
    )

    if signals_text:
        if reason:
            reason = (
                reason
                + " | Signals: "
                + signals_text
            )
        else:
            reason = (
                "Signals: "
                + signals_text
            )

    needle_score = item.get(
        "needle_score",
        item.get("score"),
    )

    score = item.get(
        "score",
        item.get("deterministic_score", 0.0),
    )

    state_source = item.get(
        "source",
        "arxiv",
    )

    db.execute(
        """
        INSERT INTO research_papers(
            arxiv_id,
            url,
            title,
            authors,
            abstract,
            published_at,
            updated_at,
            categories,
            source,
            deterministic_score,
            needle_score,
            score,
            interesting,
            researched,
            reason,
            technical_area,
            implementation_url,
            notified,
            notified_at,
            notion_page_id,
            notion_url
        )
        VALUES(
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        ON CONFLICT(arxiv_id) DO UPDATE SET
            url=excluded.url,
            title=excluded.title,
            authors=excluded.authors,
            abstract=excluded.abstract,
            published_at=excluded.published_at,
            updated_at=excluded.updated_at,
            categories=excluded.categories,
            source=excluded.source,
            deterministic_score=excluded.deterministic_score,
            needle_score=excluded.needle_score,
            score=excluded.score,
            interesting=excluded.interesting,
            researched=excluded.researched,
            reason=excluded.reason,
            technical_area=excluded.technical_area,
            implementation_url=excluded.implementation_url
        """,
        (
            arxiv_id,
            url,
            item.get("title", ""),
            authors,
            item.get("abstract", ""),
            item.get(
                "published_at",
                item.get("published", ""),
            ),
            item.get(
                "updated_at",
                item.get("updated", ""),
            ),
            categories,
            state_source,
            item.get(
                "deterministic_score",
                0.0,
            ),
            needle_score,
            score,
            int(
                bool(
                    item.get(
                        "interesting",
                        False,
                    )
                )
            ),
            int(
                bool(
                    item.get(
                        "researched",
                        False,
                    )
                )
            ),
            reason,
            item.get(
                "technical_area",
                "",
            ),
            item.get(
                "implementation_url"
            ),
            int(
                bool(
                    item.get(
                        "notified",
                        False,
                    )
                )
            ),
            item.get("notified_at"),
            item.get("notion_page_id"),
            item.get("notion_url"),
        ),
    )

    db.commit()

def research_paper_candidates(n=50):
    rows = db.execute(
        """
        SELECT *
        FROM research_papers
        WHERE interesting=0
        ORDER BY published_at DESC, created_at DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    return [dict(r) for r in rows]


def interesting_research_papers(n=20):
    rows = db.execute(
        """
        SELECT *
        FROM research_papers
        WHERE interesting=1
        ORDER BY score DESC, published_at DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    return [dict(r) for r in rows]


def unnotified_research_papers(n=20):
    rows = db.execute(
        """
        SELECT *
        FROM research_papers
        WHERE interesting=1
          AND notified=0
        ORDER BY score DESC, published_at DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    return [dict(r) for r in rows]


def mark_research_papers_notified(arxiv_ids):
    if not arxiv_ids:
        return

    now = datetime.now(
        ZoneInfo(settings.timezone)
    ).isoformat()

    db.executemany(
        """
        UPDATE research_papers
        SET notified=1,
            notified_at=?
        WHERE arxiv_id=?
        """,
        [
            (now, arxiv_id)
            for arxiv_id in arxiv_ids
        ],
    )

    db.commit()

# --- GitHub repository persistence ---

db.execute("""
CREATE TABLE IF NOT EXISTS github_repositories(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo TEXT UNIQUE NOT NULL,
    name TEXT,
    description TEXT,
    url TEXT,
    stars INTEGER DEFAULT 0,
    forks INTEGER DEFAULT 0,
    updated_at TEXT,
    category TEXT,
    score REAL,
    raw_score REAL,
    technical_signals TEXT,
    research_signals TEXT,
    readme_signals TEXT,
    readme_verified INTEGER DEFAULT 0,
    interesting INTEGER DEFAULT 0,
    notified INTEGER DEFAULT 0,
    notified_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

article_columns = {
    row[1]
    for row in db.execute(
        "PRAGMA table_info(articles)"
    ).fetchall()
}

if "notified" not in article_columns:
    db.execute(
        "ALTER TABLE articles ADD COLUMN notified INTEGER DEFAULT 0"
    )

if "notified_at" not in article_columns:
    db.execute(
        "ALTER TABLE articles ADD COLUMN notified_at TEXT"
    )

db.commit()


def upsert_github_repository(item):
    db.execute(
        """
        INSERT INTO github_repositories(
            repo,
            name,
            description,
            url,
            stars,
            forks,
            updated_at,
            category,
            score,
            raw_score,
            technical_signals,
            research_signals,
            readme_signals,
            readme_verified,
            interesting
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(repo) DO UPDATE SET
            name=excluded.name,
            description=excluded.description,
            url=excluded.url,
            stars=excluded.stars,
            forks=excluded.forks,
            updated_at=excluded.updated_at,
            category=excluded.category,
            score=excluded.score,
            raw_score=excluded.raw_score,
            technical_signals=excluded.technical_signals,
            research_signals=excluded.research_signals,
            readme_signals=excluded.readme_signals,
            readme_verified=excluded.readme_verified,
            interesting=excluded.interesting
        """,
        (
            item.get("repo"),
            item.get("name"),
            item.get("description", ""),
            item.get("url", ""),
            item.get("stars", 0),
            item.get("forks", 0),
            item.get("updated_at", ""),
            item.get("category", ""),
            item.get("score", 0.0),
            item.get("raw_score", 0.0),
            json.dumps(item.get("technical_signals", [])),
            json.dumps(item.get("research_signals", [])),
            json.dumps(item.get("readme_signals", [])),
            int(bool(item.get("readme_verified", False))),
            int(bool(item.get("interesting", False))),
        ),
    )
    db.commit()


def _github_row_to_dict(row):
    item = dict(row)

    for key in (
        "technical_signals",
        "research_signals",
        "readme_signals",
    ):
        try:
            item[key] = json.loads(item[key] or "[]")
        except Exception:
            item[key] = []

    return item


def interesting_github(n=20):
    rows = db.execute(
        """
        SELECT *
        FROM github_repositories
        WHERE interesting=1
        ORDER BY score DESC, stars DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    return [_github_row_to_dict(row) for row in rows]


def unnotified_github(n=20):
    rows = db.execute(
        """
        SELECT *
        FROM github_repositories
        WHERE interesting=1
          AND notified=0
        ORDER BY score DESC, stars DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    return [_github_row_to_dict(row) for row in rows]


def mark_github_notified(repos):
    if not repos:
        return

    now = datetime.now(
        ZoneInfo(settings.timezone)
    ).isoformat()

    db.executemany(
        """
        UPDATE github_repositories
        SET notified=1,
            notified_at=?
        WHERE repo=?
        """,
        [(now, repo) for repo in repos],
    )

    db.commit()


# --- Hugging Face model persistence ---

db.execute("""
CREATE TABLE IF NOT EXISTS huggingface_models(
    model_id TEXT PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    author TEXT DEFAULT '',
    pipeline_tag TEXT DEFAULT '',
    library_name TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    description TEXT DEFAULT '',
    downloads INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    trending_score REAL DEFAULT 0,
    created_at_hf TEXT,
    last_modified TEXT,
    deterministic_score REAL DEFAULT 0,
    score REAL DEFAULT 0,
    interesting INTEGER DEFAULT 0,
    reason TEXT DEFAULT '',
    technical_area TEXT DEFAULT '',
    notified INTEGER DEFAULT 0,
    notified_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()


def upsert_hf_model(item):
    tags = item.get("tags") or []

    if isinstance(tags, (list, tuple, set)):
        tags = ", ".join(str(x) for x in tags if x)
    else:
        tags = str(tags or "")

    db.execute(
        """
        INSERT INTO huggingface_models(
            model_id, url, author, pipeline_tag, library_name, tags,
            description, downloads, likes, trending_score, created_at_hf,
            last_modified, deterministic_score, score, interesting, reason,
            technical_area
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(model_id) DO UPDATE SET
            url=excluded.url,
            author=excluded.author,
            pipeline_tag=excluded.pipeline_tag,
            library_name=excluded.library_name,
            tags=excluded.tags,
            description=excluded.description,
            downloads=excluded.downloads,
            likes=excluded.likes,
            trending_score=excluded.trending_score,
            created_at_hf=excluded.created_at_hf,
            last_modified=excluded.last_modified,
            deterministic_score=excluded.deterministic_score,
            score=excluded.score,
            interesting=excluded.interesting,
            reason=excluded.reason,
            technical_area=excluded.technical_area
        """,
        (
            item.get("model_id", ""),
            item.get("url", ""),
            item.get("author", ""),
            item.get("pipeline_tag", ""),
            item.get("library_name", ""),
            tags,
            item.get("description", ""),
            int(item.get("downloads") or 0),
            int(item.get("likes") or 0),
            float(item.get("trending_score") or 0),
            item.get("created_at_hf") or item.get("createdAt"),
            item.get("last_modified") or item.get("lastModified"),
            item.get("deterministic_score", 0.0),
            item.get("score", 0.0),
            int(bool(item.get("interesting", False))),
            item.get("reason", ""),
            item.get("technical_area", ""),
        ),
    )

    db.commit()


def interesting_hf_models(n=20):
    rows = db.execute(
        """
        SELECT *
        FROM huggingface_models
        WHERE interesting=1
        ORDER BY score DESC, trending_score DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    return [dict(r) for r in rows]


def unnotified_hf_models(n=20):
    rows = db.execute(
        """
        SELECT *
        FROM huggingface_models
        WHERE interesting=1
          AND notified=0
        ORDER BY score DESC, trending_score DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    return [dict(r) for r in rows]


def mark_hf_models_notified(model_ids):
    if not model_ids:
        return

    now = datetime.now(
        ZoneInfo(settings.timezone)
    ).isoformat()

    db.executemany(
        """
        UPDATE huggingface_models
        SET notified=1,
            notified_at=?
        WHERE model_id=?
        """,
        [(now, model_id) for model_id in model_ids],
    )

    db.commit()


# --- Watched opportunities (availability checker) ---

db.execute("""
CREATE TABLE IF NOT EXISTS opportunities(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    note TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'unknown',
    last_checked_at TEXT,
    last_result TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()


def list_opportunities():
    rows = db.execute(
        """
        SELECT *
        FROM opportunities
        ORDER BY id DESC
        """
    ).fetchall()

    return [dict(r) for r in rows]


def add_opportunity(url, title, note=""):
    db.execute(
        """
        INSERT INTO opportunities(url, title, note)
        VALUES(?,?,?)
        ON CONFLICT(url) DO UPDATE SET
            title=excluded.title,
            note=excluded.note
        """,
        (url, title, note),
    )

    db.commit()

    return list_opportunities()


def remove_opportunity(opportunity_id):
    db.execute(
        "DELETE FROM opportunities WHERE id=?",
        (opportunity_id,),
    )

    db.commit()


def opportunities_to_check():
    """Opportunities that are not currently marked available."""
    rows = db.execute(
        """
        SELECT *
        FROM opportunities
        WHERE status != 'available'
        ORDER BY id
        """
    ).fetchall()

    return [dict(r) for r in rows]


def update_opportunity_status(opportunity_id, status, last_result=""):
    now = datetime.now(
        ZoneInfo(settings.timezone)
    ).isoformat()

    db.execute(
        """
        UPDATE opportunities
        SET status=?,
            last_checked_at=?,
            last_result=?
        WHERE id=?
        """,
        (status, now, last_result, opportunity_id),
    )

    db.commit()


# --- Kaggle item persistence ---

db.execute("""
CREATE TABLE IF NOT EXISTS kaggle_items(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT DEFAULT '',
    subtitle TEXT DEFAULT '',
    deterministic_score REAL DEFAULT 0,
    score REAL DEFAULT 0,
    interesting INTEGER DEFAULT 0,
    reason TEXT DEFAULT '',
    notified INTEGER DEFAULT 0,
    notified_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()


def upsert_kaggle_item(item):
    db.execute(
        """
        INSERT INTO kaggle_items(
            item_id, kind, title, url, subtitle,
            deterministic_score, score, interesting, reason
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(item_id) DO UPDATE SET
            kind=excluded.kind,
            title=excluded.title,
            url=excluded.url,
            subtitle=excluded.subtitle,
            deterministic_score=excluded.deterministic_score,
            score=excluded.score,
            interesting=excluded.interesting,
            reason=excluded.reason
        """,
        (
            item.get("item_id", ""),
            item.get("kind", ""),
            item.get("title", ""),
            item.get("url", ""),
            item.get("subtitle", ""),
            item.get("deterministic_score", 0.0),
            item.get("score", 0.0),
            int(bool(item.get("interesting", False))),
            item.get("reason", ""),
        ),
    )

    db.commit()


def interesting_kaggle(n=20):
    rows = db.execute(
        """
        SELECT *
        FROM kaggle_items
        WHERE interesting=1
        ORDER BY score DESC, id DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    return [dict(r) for r in rows]


def unnotified_kaggle(n=20):
    rows = db.execute(
        """
        SELECT *
        FROM kaggle_items
        WHERE interesting=1
          AND notified=0
        ORDER BY score DESC, id DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    return [dict(r) for r in rows]


def mark_kaggle_notified(item_ids):
    if not item_ids:
        return

    now = datetime.now(
        ZoneInfo(settings.timezone)
    ).isoformat()

    db.executemany(
        """
        UPDATE kaggle_items
        SET notified=1,
            notified_at=?
        WHERE item_id=?
        """,
        [(now, item_id) for item_id in item_ids],
    )

    db.commit()


# --- Simple key/value store (scheduler bookkeeping) ---

db.execute("""
CREATE TABLE IF NOT EXISTS kv(
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

db.commit()


def set_kv(key, value):
    db.execute(
        """
        INSERT INTO kv(key, value)
        VALUES(?,?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value
        """,
        (key, str(value)),
    )

    db.commit()


def get_kv(key, default=None):
    row = db.execute(
        "SELECT value FROM kv WHERE key=?",
        (key,),
    ).fetchone()

    return row["value"] if row else default
