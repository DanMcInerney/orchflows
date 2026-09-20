"""Recompute survey math and inspect source structure, without rendering claims."""
import csv
from html.parser import HTMLParser
import math
import re


def aggregate(rows):
    scores = [int(row['satisfaction']) for row in rows if row['satisfaction']]
    answers = [row['recommend'] for row in rows if row['recommend']]
    favorable = sum(score >= 4 for score in scores)
    yes = answers.count('yes')
    return {
        'responses': len(rows),
        'satisfaction': {'answered': len(scores), 'missing': len(rows) - len(scores),
                         'mean': sum(scores) / len(scores) if scores else None,
                         'favorable': favorable,
                         'pct_favorable': 100 * favorable / len(scores) if scores else None},
        'recommend': {'answered': len(answers), 'missing': len(rows) - len(answers),
                      'yes': yes, 'pct_yes': 100 * yes / len(answers) if answers else None},
    }


def matches(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and matches(actual[key], value) for key, value in expected.items())
    if expected is None:
        return actual is None
    if type(expected) is int:
        return type(actual) in (int, float) and math.isfinite(actual) and actual == expected
    return (type(actual) in (int, float) and math.isfinite(actual)
            and abs(actual - expected) <= .011)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text, self.ignored, self.charts, self.svg_stack = [], [], [], []
        self.tables = self.styles = self.headings = self.mains = 0
        self.external, self.lang = [], ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.lang = attrs.get('lang', '')
        self.tables += tag == 'table'
        self.styles += tag == 'style' or bool(attrs.get('style'))
        self.headings += tag == 'h1' or (attrs.get('role') == 'heading' and attrs.get('aria-level') == '1')
        self.mains += tag == 'main' or attrs.get('role') == 'main'
        if tag in {'head', 'script', 'style'}:
            self.ignored.append(tag)
        if tag == 'svg':
            self.charts.append({'marks': 0, 'text': []})
            self.svg_stack.append(len(self.charts) - 1)
        if self.svg_stack and tag in {'rect', 'path', 'circle', 'line', 'polygon', 'polyline'}:
            self.charts[self.svg_stack[-1]]['marks'] += 1
        for name in ('src', 'href', 'xlink:href'):
            value = attrs.get(name, '')
            if value and not value.startswith(('#', 'data:')) and tag != 'a':
                self.external.append(value)

    def handle_endtag(self, tag):
        if tag == 'svg' and self.svg_stack:
            self.svg_stack.pop()
        if self.ignored and self.ignored[-1] == tag:
            self.ignored.pop()

    def handle_data(self, data):
        if not self.ignored:
            self.text.append(data)
            if self.svg_stack:
                self.charts[self.svg_stack[-1]]['text'].append(data)


def check(c):
    with (c.stage() / 'survey.csv').open(encoding='utf-8', newline='') as source:
        rows = list(csv.DictReader(source))
    expected = {'overall': aggregate(rows)}
    for dimension in ('department', 'tenure'):
        groups = {row[dimension] or 'Unknown' for row in rows}
        expected[dimension] = {group: aggregate([row for row in rows
            if (row[dimension] or 'Unknown') == group]) for group in groups}
    actual = c.json(c.stage() / 'summary.json')
    c.require(matches(actual, expected), 'Correct overall and segment counts, means and denominators',
              'summary.json compared with independent survey.csv aggregation; tolerance 0.011 percentage points')
    for dimension in ('department', 'tenure'):
        value = actual.get(dimension) if isinstance(actual, dict) else None
        c.require(isinstance(value, dict) and set(value) == set(expected[dimension]),
                  'Include exactly the observed ' + dimension + ' groups', 'summary.json')
    path = c.stage() / 'report.html'
    c.require(path.is_file(), 'Deliver report.html', str(path))
    if path.is_file():
        page = Page()
        source = path.read_text(encoding='utf-8', errors='replace')
        page.feed(source)
        text = ' '.join(' '.join(page.text).split())
        c.require(page.lang.lower().split('-')[0] == 'en' and page.headings == 1 and page.mains == 1
                  and page.styles > 0 and page.tables > 0,
                  'Report source contains English structure, inline styling and data tables', str(path))
        charts = [chart for chart in page.charts if chart['marks'] and ''.join(chart['text']).strip()]
        css_urls = re.findall(r'url\(\s*[\'\"]?([^\s)\'\"]+)', source, re.IGNORECASE)
        c.require(len(charts) >= 2 and not page.external and '@import' not in source.lower()
                  and all(url.startswith(('#', 'data:')) for url in css_urls),
                  'Report source contains two labeled inline SVG charts without external assets', str(path))
        c.require(all(group in text for dimension in ('department', 'tenure') for group in expected[dimension]),
                  'Report source names every observed segment', str(path))
    path = c.stage() / 'checks.md'
    c.require(path.is_file() and bool(path.read_text(encoding='utf-8').strip()),
              'Deliver account of checks and limitations', str(path))
