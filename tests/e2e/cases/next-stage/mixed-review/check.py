"""Basic artifact checks; rendering and review coverage remain evidence questions."""
from html.parser import HTMLParser
import re


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.text = set(), [], []
        self.hidden = 0
        self.h1, self.main = 0, 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag in ('style', 'script'):
            self.hidden += 1
        self.h1 += tag == 'h1'
        self.main += tag == 'main' or attrs.get('role') == 'main'

    def handle_endtag(self, tag):
        if tag in ('style', 'script'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, text):
        if not self.hidden:
            self.text.append(text)


def check(c):
    workspace = c.stage()
    path = workspace / 'index.html'
    c.require(path.is_file(), 'Deliver the corrected page at index.html', str(path))
    if not path.is_file():
        return
    html = path.read_text(encoding='utf-8')
    page = Page()
    page.feed(html)
    visible = re.sub(r'\s+', ' ', ' '.join(page.text))
    brief = c.json(workspace / 'brief.json')
    facts = [brief['title'], brief['venue'], brief['price']]
    facts += [value for item in brief['sessions'] for value in (item['title'], item['time'])]
    c.require(all(value in visible for value in facts), 'Preserve event identity, price and session facts', str(path))
    c.require(page.h1 == 1 and page.main == 1, 'Provide one main heading and main landmark', str(path))
    fragments = [link[1:] for link in page.links if link.startswith('#')]
    c.require(bool(fragments) and all(fragment in page.ids for fragment in fragments),
              'Provide in-page navigation without broken fragment targets', str(path))
    c.require(not any(claim in visible.lower() for claim in ('highest-rated', '10,000', '10000')),
              'Remove unsupported seeded popularity claims', str(path))
    c.require((workspace / 'checks.md').is_file(), 'Report checks and capability gaps', str(workspace / 'checks.md'))
