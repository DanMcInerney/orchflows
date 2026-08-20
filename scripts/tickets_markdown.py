"""Private byte-preserving Markdown mechanics for the ticket format owner."""
from __future__ import annotations

EXECUTOR_SECTIONS = ('Result', 'Verification', 'Feedback', 'Risks', 'Handoff')
EXECUTOR_SECTIONS_BY_KEY = {name.lower(): name for name in EXECUTOR_SECTIONS}
CUT_SECTIONS = ('Objective', 'Fixed inputs', 'Completion test', 'Return fields')
CUT_SECTIONS_BY_KEY = {name.lower(): name for name in CUT_SECTIONS}
SECTION_ORDER = CUT_SECTIONS + EXECUTOR_SECTIONS
SECTION_RANK = {name.lower(): i for i, name in enumerate(SECTION_ORDER)}
OPTIONAL_SECTION = 'Handoff'
REQUIRED_SECTIONS = tuple(name for name in SECTION_ORDER if name != OPTIONAL_SECTION)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
        return value[1:-1]
    return value


def _parse_frontmatter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
    if end is None:
        return {}
    data, i = {}, 1
    while i < end:
        line, stripped = lines[i], lines[i].strip()
        if not stripped or stripped.startswith('#') or ':' not in line:
            i += 1
            continue
        key, _, rest = line.partition(':')
        key, rest = key.strip(), rest.strip()
        if rest == '':
            items, j = [], i + 1
            while j < end:
                item = lines[j].strip()
                if item.startswith('- '):
                    items.append(_unquote(item[2:].strip()))
                    j += 1
                elif item == '-':
                    j += 1
                else:
                    break
            data[key], i = items, j if items else i + 1
        elif rest.startswith('[') and rest.endswith(']'):
            inner = rest[1:-1].strip()
            data[key], i = ([] if not inner else [_unquote(p.strip()) for p in inner.split(',')]), i + 1
        else:
            data[key], i = _unquote(rest), i + 1
    return data


def _frontmatter_bounds(text: str):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip('\r\n') != '---':
        raise ValueError('ticket is missing frontmatter')
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip('\r\n') == '---'), None)
    if end is None:
        raise ValueError('ticket frontmatter is not terminated')
    return lines, end


def _field_matches(lines, end: int, key: str):
    return [i for i in range(1, end) if ':' in lines[i] and lines[i].split(':', 1)[0].strip() == key]


def _frontmatter_line(key: str, value: str, newline: str) -> str:
    return f'{key}: {value}{newline}' if value != '' else f'{key}:{newline}'


def _set_frontmatter_field(text: str, key: str, value: str) -> str:
    lines, end = _frontmatter_bounds(text)
    newline = '\r\n' if lines[0].endswith('\r\n') else '\n'
    matches = _field_matches(lines, end, key)
    if len(matches) > 1:
        raise ValueError(f"ticket frontmatter repeats '{key}'")
    if matches:
        lines[matches[0]] = _frontmatter_line(key, value, newline)
    else:
        lines.insert(end, _frontmatter_line(key, value, newline))
    return ''.join(lines)


def _remove_frontmatter_field(text: str, key: str) -> str:
    lines, end = _frontmatter_bounds(text)
    matches = _field_matches(lines, end, key)
    if len(matches) > 1:
        raise ValueError(f"ticket frontmatter repeats '{key}'")
    for i in matches:
        stop = i + 1
        if lines[i].split(':', 1)[1].strip() == '':
            while stop < end and lines[stop].strip().startswith('-'):
                stop += 1
        del lines[i:stop]
        return ''.join(lines)
    return text


def _duplicate_frontmatter_keys(text: str) -> list:
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return []
    seen, duplicates = set(), set()
    for line in lines[1:]:
        if line.strip() == '---':
            break
        if not line.strip() or line.lstrip().startswith(('#', '-')) or ':' not in line:
            continue
        key = line.split(':', 1)[0].strip()
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return sorted(duplicates)


class TicketFormatError(ValueError):
    """The ticket Markdown cannot be written safely as it stands."""


def _fence_run(line: str):
    if line.startswith('\t') or len(line) - len(line.lstrip(' ')) >= 4:
        return None
    stripped = line.strip()
    for char in ('`', '~'):
        if stripped.startswith(char * 3):
            return char * (len(stripped) - len(stripped.lstrip(char)))
    return None


def _scan_sections(lines, start: int = 0):
    found, fence, opened_at = [], None, None
    for i in range(start, len(lines)):
        line, run = lines[i], _fence_run(lines[i])
        if fence is None:
            if run is not None:
                fence, opened_at = run, i
            elif line.startswith('## '):
                found.append(i)
        elif run is not None and run[0] == fence[0] and len(run) >= len(fence) and not line.strip()[len(run):].strip():
            fence, opened_at = None, None
    return found, opened_at


def _heading_lines(lines, start: int = 0) -> list:
    return _scan_sections(lines, start)[0]


def _sections(text: str) -> dict:
    sections, heading, body = {}, None, []
    lines = text.splitlines()
    starts = set(_heading_lines(lines))
    for i, line in enumerate(lines):
        if i in starts:
            if heading is not None:
                sections[heading] = '\n'.join(body).strip()
            raw = line[3:].strip()
            heading = CUT_SECTIONS_BY_KEY.get(raw.lower()) or EXECUTOR_SECTIONS_BY_KEY.get(raw.lower()) or raw
            body = []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        sections[heading] = '\n'.join(body).strip()
    return sections


def _frontmatter_end(lines) -> int:
    if not lines or lines[0].rstrip('\r\n') != '---':
        return 0
    for i in range(1, len(lines)):
        if lines[i].rstrip('\r\n') == '---':
            return i + 1
    return 0


def _section_body(text: str, heading: str) -> str:
    lines = text.splitlines()
    starts, _ = _scan_sections(lines, _frontmatter_end(lines))
    for position, index in enumerate(starts):
        if lines[index][3:].strip().lower() == heading.strip().lower():
            end = starts[position + 1] if position + 1 < len(starts) else len(lines)
            return '\n'.join(lines[index + 1:end]).strip()
    return ''


def _body_block(body: str, newline: str) -> str:
    normalized = body.replace('\r\n', '\n').replace('\r', '\n').strip('\n')
    return '' if not normalized else newline.join(normalized.split('\n')) + newline


def _write_section(text: str, heading: str, body: str, append: bool = False) -> str:
    lines = text.splitlines(keepends=True)
    newline = '\r\n' if lines and lines[0].endswith('\r\n') else '\n'
    starts, unclosed = _scan_sections(lines, _frontmatter_end(lines))
    if unclosed is not None:
        raise TicketFormatError(f"unterminated fence opened at line {unclosed + 1} ({lines[unclosed].strip()}): every heading below it reads as quoted content, so writing '## {heading}' would create a second one. Close the fence in the ticket, then retry")
    found = next((i for i in starts if lines[i][3:].strip().lower() == heading.lower()), None)
    if found is None:
        block = _body_block(body, newline)
        segment = f'## {heading}{newline}{newline}{block}' if block else f'## {heading}{newline}'
        target_rank = SECTION_RANK.get(heading.lower())
        insert_at = next((i for i in starts if SECTION_RANK.get(lines[i][3:].strip().lower(), -1) > target_rank), None) if target_rank is not None else None
        if insert_at is None:
            prefix = ''.join(lines).rstrip('\r\n')
            return (prefix + newline + newline if prefix else '') + segment
        return ''.join(lines[:insert_at]) + segment + newline + ''.join(lines[insert_at:])
    end = next((i for i in starts if i > found), len(lines))
    if append:
        prior = ''.join(lines[found + 1:end]).rstrip().lstrip('\r\n')
        if prior:
            body = f'{prior}\n\n{body}'
    block, head = _body_block(body, newline), lines[found]
    if not head.endswith('\n'):
        head += newline
    segment = head + newline + block if block else head
    if end < len(lines):
        segment += newline
    return ''.join(lines[:found]) + segment + ''.join(lines[end:])
