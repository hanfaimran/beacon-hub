import glob, sqlite3
for p in glob.glob("*.db"):
    c = sqlite3.connect(p)
    try:
        print(p, c.execute("SELECT domain, category, COUNT(*) FROM opportunities GROUP BY 1,2").fetchall())
    except Exception as e:
        print(p, "skip", e)