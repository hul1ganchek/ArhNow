import sqlite3

db_name = "ArhNow.db"

def db_conn():
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def db_save_section(title):
    with db_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO sections(title) VALUES (?)", (title,))
        row = conn.execute("SELECT id FROM sections WHERE title = ?", (title,)).fetchone()
        return row["id"] if row else None

def db_save_subsection(section_id, parent_id, title, url, type_):
    with db_conn() as conn:
        conn.execute("""
            INSERT INTO subsections(section_id, parent_id, title, url, type)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                section_id = excluded.section_id,
                parent_id = excluded.parent_id,
                title = excluded.title,
                type = excluded.type
        """, (section_id, parent_id, title, url, type_))
        row = conn.execute("SELECT id FROM subsections WHERE url = ?", (url,)).fetchone()
        return row["id"] if row else None

def db_save_document(subsection_id, title, url, description):
    with db_conn() as conn:
        conn.execute("""
            INSERT INTO documents(subsection_id, title, url, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                subsection_id = excluded.subsection_id,
                title = excluded.title,
                description = excluded.description,
                parsed_at = CURRENT_TIMESTAMP
        """, (subsection_id, title, url, description))
        row = conn.execute("SELECT id FROM documents WHERE url = ?", (url,)).fetchone()
        return row["id"] if row else None

def db_save_history(vk_id, action, subsection_id=None, document_id=None):
    with db_conn() as conn:
        conn.execute("""
            INSERT INTO users_history(vk_id, action, subsection_id, document_id)
            VALUES (?, ?, ?, ?)
        """, (vk_id, action, subsection_id, document_id))

def db_save_items(section_id, parent_id, items):
    for item in items:
        db_save_subsection(section_id, parent_id, item["title"], item["url"], item["type"])
