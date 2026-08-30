NASDAQ Breadth Fix V2

Replace these two files in your GitHub repository:
1. scripts/update_data.py
2. requirements.txt

Then run:
Actions -> Update Nasdaq Technical Data -> Run workflow

What changed:
- Wikipedia request now uses a browser-style User-Agent.
- Added Nasdaq official companies page as a second live source.
- Added an embedded emergency constituent fallback if both live sources fail.
- Breadth price downloads are split into chunks so one transient batch failure does not break the run.
- data/technical.json now records breadth.source and breadth.source_status.
- The existing dashboard's Breadth note will show LIVE / FALLBACK and constituent count.
