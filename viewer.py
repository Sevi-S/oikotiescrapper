#!/usr/bin/env python3
"""Simple web viewer for oikotie results.csv with editable notes."""

import csv
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

DIR = os.environ.get("RESULTS_DIR", os.path.dirname(os.path.abspath(__file__)))
RESULTS_FILE = os.path.join(DIR, "results.csv")
NOTES_FILE = os.path.join(DIR, "notes.json")


def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE) as f:
            return json.load(f)
    return {}


def save_notes(notes):
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f)


def load_results():
    rows = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, newline="") as f:
            for r in csv.DictReader(f):
                rows.append(r)
    return rows


HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Apartment Finder</title>
<style>
  body { font-family: sans-serif; margin: 20px; background: #f5f5f5; }
  table { border-collapse: collapse; width: 100%%; }
  th { background: #2c3e50; color: white; padding: 10px; text-align: left; position: sticky; top: 0; }
  td { padding: 8px 10px; border-bottom: 1px solid #ddd; }
  tr:hover { background: #e8f4fd; }
  a { color: #2980b9; }
  .notes { width: 200px; padding: 4px; border: 1px solid #ccc; border-radius: 3px; }
  .saved { background: #d4edda; transition: background 0.3s; }
  .tag { display: inline-block; background: #eee; border-radius: 3px; padding: 2px 6px; font-size: 12px; margin-right: 4px; }
</style></head><body>
<h2>🏠 Apartment Finder — %d listings</h2>
<table>
<tr><th>Date</th><th>District</th><th>Address</th><th>Rooms</th><th>m²</th><th>Price</th><th>Year</th><th>Metro</th><th>Walk</th><th>Link</th><th>Notes</th></tr>
%s
</table>
<script>
function saveNote(url, el) {
  fetch('/notes', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:'url='+encodeURIComponent(url)+'&note='+encodeURIComponent(el.value)})
  .then(()=>{el.classList.add('saved'); setTimeout(()=>el.classList.remove('saved'),1000);});
}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        rows = load_results()
        notes = load_notes()
        table_rows = []
        for r in rows:
            url = r.get("url", "")
            note = notes.get(url, "")
            table_rows.append(
                f'<tr><td>{r.get("first_seen","")}</td><td>{r.get("district","")}</td>'
                f'<td>{r.get("address","")}</td><td>{r.get("rooms","")}</td>'
                f'<td>{r.get("size_m2","")}</td><td>{r.get("price","")}</td>'
                f'<td>{r.get("year","")}</td><td>{r.get("metro","")}</td>'
                f'<td>{r.get("walk_min","")} min</td>'
                f'<td><a href="{url}" target="_blank">View</a></td>'
                f'<td><input class="notes" value="{note}" onchange="saveNote(\'{url}\',this)"></td></tr>'
            )
        html = HTML % (len(rows), "\n".join(table_rows))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = parse_qs(self.rfile.read(length).decode())
        url = data.get("url", [""])[0]
        note = data.get("note", [""])[0]
        notes = load_notes()
        notes[url] = note
        save_notes(notes)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        pass  # quiet


if __name__ == "__main__":
    port = 8080
    print(f"Serving at http://localhost:{port}")
    HTTPServer(("", port), Handler).serve_forever()
