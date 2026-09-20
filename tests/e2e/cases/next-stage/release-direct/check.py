"""Objective coverage controls; prose meaning and process require independent audit."""
import re
from datetime import date


STAGES = ('target',)
PACKAGE = False
IDS = re.compile(r'\bREL-\d{3}\b')
URLS = re.compile(r'https?://[^\s<>\])]+')
UNCERTAIN = re.compile(
    r'\b(?:unknown|undocumented|unspecified|unavailable|unconfirmed|unclear|unresolved|unreported|tbd|'
    r'not\s+(?:yet\s+)?(?:been\s+)?(?:provided|documented|specified|known|confirmed|determined|stated|supplied|available|given)|'
    r'no\s+(?:migration\s+)?(?:action|deadline|date|steps?)\s+(?:(?:is|was)\s+)?(?:provided|specified|documented|supplied|given)|'
    r'to\s+be\s+(?:confirmed|determined)|open\s+questions?|'
    r'(?:needs?|requires?)\s+(?:confirmation|clarification)|missing)\b', re.I)
FIELDS = {
    'breaking': re.compile(r'\b(?:breaking|compatibility|impact)\b', re.I),
    'action': re.compile(r'\b(?:action|migration|procedure|steps?|instructions?|upgrade)\b', re.I),
    'deadline': re.compile(r'\b(?:deadline|date|timing|cutoff|cut-off|sunset)\b', re.I),
}


def readable_markdown(text):
    """Ignore obvious hidden/dumped material without imposing a Markdown layout."""
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', text, flags=re.S | re.I)
    return re.sub(r'^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', text,
                  flags=re.S | re.M)


def prose(text):
    # A source URL containing an ID does not alone label the customer-facing item.
    text = re.sub(r'^\s*\[[^\]]+\]:\s*https?://\S+.*$', '', text, flags=re.M)
    text = re.sub(r'(!?)\[([^\]]+)\]\([^)]*\)', r'\2', text)
    return URLS.sub('', text)


def item_contexts(text):
    """Support paragraphs, item headings, bullets and table rows with continuations."""
    contexts, active, active_level = {}, set(), None
    for line in text.splitlines():
        present = set(IDS.findall(line))
        heading = re.match(r'^\s*(#{1,6})\s+', line)
        if present:
            active = present
            active_level = len(heading[1]) if heading else None
        elif heading and (active_level is None or len(heading[1]) <= active_level):
            # Retain item subheadings; a peer heading cannot lend another item's gaps.
            active = set()
        for identifier in active:
            contexts.setdefault(identifier, []).append(line)
    return {key: '\n'.join(lines) for key, lines in contexts.items()}


def contains_date(text, iso):
    """An exact date can be rendered as ISO or an unambiguous English date."""
    value = date.fromisoformat(iso)
    if re.search(r'(?<!\d)' + re.escape(iso) + r'(?!\d)', text):
        return True
    month = '(?:' + value.strftime('%B') + '|' + value.strftime('%b') + r'\.?)'
    if value.month == 9:
        month = r'(?:September|Sept?\.?)'
    day = '0?' + str(value.day) + r'(?:st|nd|rd|th)?'
    year = str(value.year)
    return bool(re.search(r'\b(?:' + month + r'\s+' + day + r'(?:,\s*|\s+)' + year
                          + '|' + day + r'\s+' + month + r'\s+' + year + r')\b', text, re.I))


def check_stage(c, stage):
    workspace = c.stage(stage)
    source = c.json(workspace / 'changes.json')
    selected = [item for item in source['changes']
                if item['status'] == 'shipped' and item['visibility'] == 'public']
    migration = [item for item in selected if item['breaking'] is not False]
    for filename, items in (('release-notes.md', selected), ('migration-checklist.md', migration)):
        path = workspace / filename
        c.require(path.is_file(), 'Deliver ' + filename, str(path))
        if not path.is_file():
            continue
        try:
            text = readable_markdown(path.read_text(encoding='utf-8'))
        except UnicodeError:
            c.require(False, 'Deliver readable Markdown', str(path))
            continue
        visible = prose(text)
        c.require(bool(visible.strip()), 'Deliver substantive visible Markdown', str(path))
        c.require(set(IDS.findall(visible)) == {item['id'] for item in items},
                  'Label exactly the changes selected for this output', str(path))
        links = {url.rstrip('.,;') for url in URLS.findall(text)}
        c.require(links == {item['source_url'] for item in items},
                  'Retain the selected source links without unrelated attribution', str(path))
        if filename == 'release-notes.md':
            c.require(all(source[key] in visible for key in ('product', 'version'))
                      and contains_date(visible, source['released_at']),
                      'Identify the supplied product, version and release date', str(path))
        contexts = item_contexts(visible)
        for item in items:
            context = contexts.get(item['id'], '')
            unknown = ['breaking'] if item['breaking'] is None else []
            if filename == 'migration-checklist.md':
                details = item['migration'] or {}
                unknown += [key for key in ('action', 'deadline') if details.get(key) is None]
                if details.get('deadline'):
                    c.require(contains_date(context, details['deadline']),
                              'Preserve the migration deadline for ' + item['id'], str(path))
            for key in unknown:
                c.require(bool((UNCERTAIN.search(context) or '?' in context) and FIELDS[key].search(context)),
                          'Visibly surface unknown ' + key + ' for ' + item['id'], str(path))
    # Presence/labels are necessary only: audit verifies each action, claim and unknown's meaning.


def check(c):
    if PACKAGE:
        library = c.root / 'generated/personal'
        for relative in ('plugin.json', '.claude-plugin/plugin.json', '.codex-plugin/plugin.json',
                         '.kimi-plugin/plugin.json', 'skills/release-brief/SKILL.md'):
            c.require((library / relative).is_file(),
                      'Deliver the frozen reusable personal package', str(library / relative))
    for stage in STAGES:
        check_stage(c, stage)
