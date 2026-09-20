"""Semantic HTML checks; rendering still needs separate evidence."""
from html.parser import HTMLParser
import json


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = ''
        self.headings = 0
        self.mains = 0
        self.styles = 0
        self.ids = set()
        self.links = []
        self.text = []
        self.ignored = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.lang = attrs.get('lang', '')
        self.headings += tag == 'h1' or (attrs.get('role') == 'heading' and attrs.get('aria-level') == '1')
        self.mains += tag == 'main' or attrs.get('role') == 'main'
        self.styles += tag == 'style' or bool(attrs.get('style'))
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag in {'head', 'script', 'style'}:
            self.ignored.append(tag)

    def handle_endtag(self, tag):
        if self.ignored and self.ignored[-1] == tag:
            self.ignored.pop()

    def handle_data(self, data):
        if not self.ignored:
            self.text.append(data)


def check(c):
    path = c.stage() / 'index.html'
    c.require(path.is_file(), 'Deliver index.html', str(path))
    if not path.is_file():
        return
    page = Page()
    page.feed(path.read_text(encoding='utf-8'))
    event = json.loads((c.stage() / 'event.json').read_text(encoding='utf-8'))
    text = ' '.join(' '.join(page.text).split())
    # Proper names, prices and times are exact; prose equivalence belongs to the audit.
    required = [event[key] for key in ('name', 'venue', 'price')]
    required += [part for item in event['sessions'] for part in (item['time'], item['title'])]
    c.require(all(value in text for value in required), 'Display supplied event identifiers and schedule', str(path))
    c.require(page.lang.lower().split('-')[0] == 'en' and page.headings == 1 and page.mains == 1,
              'English document with one heading and main landmark', str(path))
    c.require(page.styles > 0 and '#schedule' in page.links and 'schedule' in page.ids
              and 'View schedule' in text, 'Inline CSS and functional schedule link', str(path))
    report = c.stage() / 'checks.md'
    c.require(report.is_file() and bool(report.read_text(encoding='utf-8').strip()),
              'Deliver the requested account of checks and limits', str(report))
