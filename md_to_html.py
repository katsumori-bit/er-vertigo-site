from __future__ import annotations

import html
import os
import re
from pathlib import Path
from urllib.parse import quote

ER_DIR = Path(__file__).resolve().parent
# リポジトリルート＝このフォルダ（GitHub 上では親に「臨床」が無い）。走査・Wiki解決は ER_DIR 基準。
ROOT_DIR = ER_DIR
# 表示用（Obsidian 上の元パス）
SOURCE_PREFIX = "臨床/ER"
CSS_PATH = ER_DIR / "er-note.css"

RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
RE_LIST = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
RE_CALLOUT_START = re.compile(r"^>\s*\[!([A-Za-z]+)\]([+-])?\s*(.*)$")
RE_CALLOUT_LINE = re.compile(r"^>\s?(.*)$")
RE_TABLE_SEP = re.compile(r"^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")
RE_IMAGE_EXT = re.compile(r"\.(png|jpe?g|gif|webp|svg)$", re.IGNORECASE)


def normalize_rel(path: Path) -> str:
    return path.as_posix()


def make_anchor(text: str) -> str:
    plain = re.sub(r"`([^`]+)`", r"\1", text)
    plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", plain)
    plain = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", plain)
    plain = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", plain)
    plain = re.sub(r"\[\[([^\]]+)\]\]", r"\1", plain)
    plain = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff\- ]+", "", plain).strip().lower()
    return re.sub(r"\s+", "-", plain) or "section"


def rel_href(src_html: Path, dst_html: Path, anchor: str = "") -> str:
    href = os.path.relpath(dst_html, src_html.parent).replace("\\", "/")
    if anchor:
        href = f"{href}#{quote(anchor)}"
    return href


def resolve_wiki_target(
    raw_target: str, current_md: Path, all_md: set[Path], by_stem: dict[str, list[Path]]
) -> tuple[Path | None, str]:
    raw_target = raw_target.strip()
    if not raw_target:
        return None, ""
    if "#" in raw_target:
        file_part, anchor = raw_target.split("#", 1)
    else:
        file_part, anchor = raw_target, ""

    file_part = file_part.strip()
    anchor = anchor.strip()
    if not file_part:
        return current_md, anchor

    candidates: list[Path] = []
    if file_part.endswith(".md"):
        candidates.extend([current_md.parent / file_part, ROOT_DIR / file_part])
    else:
        candidates.extend(
            [
                current_md.parent / file_part,
                current_md.parent / f"{file_part}.md",
                ROOT_DIR / file_part,
                ROOT_DIR / f"{file_part}.md",
            ]
        )

    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved in all_md:
            return resolved, anchor

    if "/" not in file_part and "\\" not in file_part:
        hits = by_stem.get(file_part, [])
        if len(hits) == 1:
            return hits[0], anchor
        for hit in hits:
            if hit.parent == current_md.parent:
                return hit, anchor
    return None, anchor


def render_inline(
    text: str, current_md: Path, all_md: set[Path], by_stem: dict[str, list[Path]]
) -> str:
    code_map: dict[str, str] = {}

    def _stash_code(match: re.Match[str]) -> str:
        key = f"@@CODE{len(code_map)}@@"
        code_map[key] = f"<code>{html.escape(match.group(1))}</code>"
        return key

    text = re.sub(r"`([^`]+)`", _stash_code, text)
    text = html.escape(text)

    def repl_embed_wiki(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        target = raw.split("|", 1)[0].strip()
        if RE_IMAGE_EXT.search(target):
            img_src = normalize_rel(Path(target))
            return f'<img class="embed-image" src="{img_src}" alt="{html.escape(target)}" loading="lazy" />'
        return f'<span class="wiki-missing">{html.escape(raw)}</span>'

    def repl_md_image(match: re.Match[str]) -> str:
        alt = match.group(1)
        src = match.group(2).strip()
        safe_src = src[:-3] + ".html" if src.endswith(".md") else src
        return f'<img class="embed-image" src="{safe_src}" alt="{alt}" loading="lazy" />'

    def repl_md_link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = match.group(2).strip()
        safe_href = href[:-3] + ".html" if href.endswith(".md") else href
        return f'<a class="wiki-link" href="{safe_href}">{label}</a>'

    def repl_wiki(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        if "|" in raw:
            target, label = raw.split("|", 1)
        else:
            target, label = raw, raw
        target = target.strip()
        label = label.strip()
        src_html = current_md.with_suffix(".html")

        if target.startswith("#"):
            anchor_text = target[1:].strip()
            if not anchor_text:
                return f'<span class="wiki-missing">{label}</span>'
            href = rel_href(src_html, src_html, make_anchor(anchor_text))
            return f'<a class="wiki-link" href="{href}">{label}</a>'

        resolved, anchor = resolve_wiki_target(target, current_md, all_md, by_stem)
        if resolved is None:
            return f'<span class="wiki-missing">{label}</span>'
        dst_html = resolved.with_suffix(".html")
        href = rel_href(src_html, dst_html, make_anchor(anchor) if anchor else "")
        return f'<a class="wiki-link" href="{href}">{label}</a>'

    text = re.sub(r"!\[\[([^\]]+)\]\]", repl_embed_wiki, text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl_md_image, text)
    text = re.sub(r"\[\[([^\]]+)\]\]", repl_wiki, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl_md_link, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)

    for key, value in code_map.items():
        text = text.replace(html.escape(key), value)
    return text


def parse_table(
    lines: list[str], i: int, current_md: Path, all_md: set[Path], by_stem: dict[str, list[Path]]
) -> tuple[str, int]:
    table_lines: list[str] = []
    while i < len(lines) and "|" in lines[i] and lines[i].strip():
        table_lines.append(lines[i].rstrip())
        i += 1
    if len(table_lines) < 2 or not RE_TABLE_SEP.match(table_lines[1]):
        return "", i - len(table_lines)

    header_cells = [c.strip() for c in table_lines[0].strip("|").split("|")]
    body_lines = table_lines[2:]
    parts = ['<div class="table-wrap"><table><thead><tr>']
    for cell in header_cells:
        parts.append(f"<th>{render_inline(cell, current_md, all_md, by_stem)}</th>")
    parts.append("</tr></thead><tbody>")
    for row in body_lines:
        cells = [c.strip() for c in row.strip("|").split("|")]
        parts.append("<tr>")
        for cell in cells:
            parts.append(f"<td>{render_inline(cell, current_md, all_md, by_stem)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts), i


def render_blocks(lines: list[str], current_md: Path, all_md: set[Path], by_stem: dict[str, list[Path]]) -> str:
    out: list[str] = []
    para: list[str] = []
    list_stack: list[tuple[str, int]] = []
    in_fold = False

    def close_para() -> None:
        if not para:
            return
        text = " ".join(p.strip() for p in para if p.strip())
        if text:
            out.append(f"<p>{render_inline(text, current_md, all_md, by_stem)}</p>")
        para.clear()

    def close_lists(to_indent: int = -1) -> None:
        if to_indent < 0:
            while list_stack:
                out.append(f"</{list_stack.pop()[0]}>")
            return
        while list_stack and list_stack[-1][1] >= to_indent:
            out.append(f"</{list_stack.pop()[0]}>")

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()

        if not stripped:
            close_para()
            close_lists()
            i += 1
            continue

        m_callout = RE_CALLOUT_START.match(line)
        if m_callout:
            close_para()
            close_lists()
            callout_type = m_callout.group(1).lower()
            collapse_flag = m_callout.group(2)
            title = m_callout.group(3).strip() or callout_type.title()
            body_lines: list[str] = []
            i += 1
            while i < len(lines):
                m_body = RE_CALLOUT_LINE.match(lines[i])
                if not m_body:
                    break
                body_lines.append(m_body.group(1))
                i += 1
            body_html = render_blocks(body_lines, current_md, all_md, by_stem)
            klass = f"callout callout-{callout_type}"
            if collapse_flag:
                open_attr = "" if collapse_flag == "-" else " open"
                out.append(f'<details class="{klass}"{open_attr}>')
                out.append(
                    f"<summary>{render_inline(title, current_md, all_md, by_stem)}</summary><div class=\"callout-body\">{body_html}</div>"
                )
                out.append("</details>")
            else:
                out.append(f'<div class="{klass}">')
                out.append(f'<div class="callout-title">{render_inline(title, current_md, all_md, by_stem)}</div>')
                out.append(f'<div class="callout-body">{body_html}</div>')
                out.append("</div>")
            continue

        m_head = RE_HEADING.match(line)
        if m_head:
            close_para()
            close_lists()
            level = len(m_head.group(1))
            text = m_head.group(2).strip()
            hid = make_anchor(text)
            if level == 2 and "折りたたみ" in text:
                if in_fold:
                    out.append("</details>")
                out.append(
                    f"<details class=\"section-fold\"><summary id=\"{hid}\">{render_inline(text, current_md, all_md, by_stem)}</summary>"
                )
                in_fold = True
            else:
                out.append(f"<h{level} id=\"{hid}\">{render_inline(text, current_md, all_md, by_stem)}</h{level}>")
            i += 1
            continue

        if stripped in {"---", "***", "___"}:
            close_para()
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        if "|" in line:
            table_html, next_i = parse_table(lines, i, current_md, all_md, by_stem)
            if table_html:
                close_para()
                close_lists()
                out.append(table_html)
                i = next_i
                continue

        m_list = RE_LIST.match(line)
        if m_list:
            close_para()
            indent = len(m_list.group(1).replace("\t", "    "))
            marker = m_list.group(2)
            text = m_list.group(3).strip()
            tag = "ol" if marker.endswith(".") else "ul"
            while list_stack and indent < list_stack[-1][1]:
                out.append(f"</{list_stack.pop()[0]}>")
            if not list_stack or indent > list_stack[-1][1] or list_stack[-1][0] != tag:
                out.append(f"<{tag}>")
                list_stack.append((tag, indent))
            out.append(f"<li>{render_inline(text, current_md, all_md, by_stem)}</li>")
            i += 1
            continue

        para.append(line)
        i += 1

    close_para()
    close_lists()
    if in_fold:
        out.append("</details>")
    return "\n".join(out)


def css_href_for(md_path: Path) -> str:
    html_dir = md_path.with_suffix(".html").parent
    return os.path.relpath(CSS_PATH, html_dir).replace("\\", "/")


def build_html(md_path: Path, body_html: str) -> str:
    source_rel = f"{SOURCE_PREFIX}/{normalize_rel(md_path.relative_to(ER_DIR))}"
    title = md_path.stem
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light only" />
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{css_href_for(md_path)}" />
</head>
<body>
  <article class="note-shell">
    <header class="note-header">
      <h1>{html.escape(title)}</h1>
      <p class="source-badge">元: {html.escape(source_rel)}</p>
    </header>
    <div class="md-body">
{body_html}
    </div>
  </article>
</body>
</html>
"""


def ensure_heading_ids(body_html: str) -> str:
    def repl(match: re.Match[str]) -> str:
        level = match.group(1)
        attrs = match.group(2)
        inner = match.group(3)
        if re.search(r'\bid\s*=\s*["\']', attrs):
            return match.group(0)
        plain = re.sub(r"<[^>]+>", "", inner)
        hid = make_anchor(html.unescape(plain))
        return f"<h{level}{attrs} id=\"{hid}\">{inner}</h{level}>"

    return re.sub(r"<h([1-6])([^>]*)>(.*?)</h\1>", repl, body_html, flags=re.DOTALL)


def collect_target_mds() -> list[Path]:
    md_files: list[Path] = []
    for md in ER_DIR.rglob("*.md"):
        if ".git" in md.parts:
            continue
        if md.name == "README.md":
            continue
        md_files.append(md.resolve())
    return sorted(md_files)


def main() -> None:
    md_files = collect_target_mds()
    all_md = set(md_files)
    by_stem: dict[str, list[Path]] = {}
    for md in md_files:
        by_stem.setdefault(md.stem, []).append(md)

    for md in md_files:
        lines = md.read_text(encoding="utf-8").splitlines()
        body = render_blocks(lines, md, all_md, by_stem)
        body = ensure_heading_ids(body)
        md.with_suffix(".html").write_text(build_html(md, body), encoding="utf-8")


if __name__ == "__main__":
    main()
