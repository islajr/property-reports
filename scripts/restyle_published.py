"""Restyle published reports without changing their content or metadata."""
import argparse
from pathlib import Path
import re
import shutil
import tinycss2
import tempfile
from jinja2 import Environment, FileSystemLoader
from render_report import build_embedded_fonts_css, render_pdf

ROOT = Path(__file__).resolve().parents[1]


def strip_legacy_print_styles(html):
    """Discard only obsolete head print rules; retain screen CSS and report body."""
    head, body = html.split('<body>', 1)
    def clean(match):
        rules = tinycss2.parse_stylesheet(match.group(1), skip_whitespace=False, skip_comments=False)
        kept = [rule for rule in rules if not (
            rule.type == 'at-rule' and rule.lower_at_keyword == 'media'
            and tinycss2.serialize(rule.prelude).strip().lower() == 'print')]
        return '<style>' + tinycss2.serialize(kept) + '</style>'
    head = re.sub(r'<style>\s*(.*?)</style>', clean, head, flags=re.S)
    return re.sub(r'[ \t]+(?=\n)', '', head) + '<body>' + body


def pdf_compatible_svg(html):
    """Resolve SVG custom properties unsupported by the pinned PDF renderer."""
    palette = {
        'bg-card': '#fffefa', 'bg-card-alt': '#f4f2eb', 'border': '#dfdfd5',
        'text-primary': '#222c25', 'text-secondary': '#5d685f',
        'gold-light': '#222c25', 'gold': '#74491c',
        'font-sans': "'New Computer Modern', Georgia, serif",
    }
    def resolve(match):
        svg = match.group()
        for name, value in palette.items():
            svg = svg.replace(f'var(--{name})', value)
        return svg
    return re.sub(r'<svg\b.*?</svg>', resolve, html, flags=re.S)


def restyle(source, destination, pdf=True):
    if destination.resolve() == (ROOT / 'reports').resolve() or (ROOT / 'reports').resolve() in destination.resolve().parents:
        raise ValueError('Presentation review output must be outside the published archive.')
    destination.mkdir(parents=True, exist_ok=True)
    original = (source / 'index.html').read_text()
    # The old site header is the only removed body markup. Report prose is untouched.
    original_header = re.search(r'<header class="global-header">.*?</header>|<header class="site-header">.*?</header>\s*<div id="main-content" tabindex="-1"></div>', original, re.S)
    if not original_header:
        raise ValueError('Expected a recognised published report header.')
    env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=True)
    shared_header = env.get_template('partials/header.html.j2').render().strip() + '<div id="main-content" tabindex="-1"></div>'
    css = (ROOT / 'templates/partials/site.css').read_text() + (ROOT / 'templates/partials/published-report.css').read_text()
    style = '<style id="publication-presentation">' + build_embedded_fonts_css() + css + '</style>'
    script = '<script id="publication-theme">' + (ROOT / 'templates/partials/theme.js').read_text() + '</script>'
    head, body = original.split('<body>', 1)
    head = re.sub(r'<style id="publication-presentation">.*?</style>', '', head, flags=re.S)
    head = re.sub(r'<script(?: id="publication-theme")?>(.*?)</script>', lambda match: '' if 'reports-theme' in match.group(1) and 'document.documentElement' in match.group(1) else match.group(), head, flags=re.S)
    clean_original = head + '<body>' + body
    updated = strip_legacy_print_styles(clean_original).replace('</head>', style + script + '</head>', 1).replace(original_header.group(), shared_header, 1)
    # Verify all original report markup survives exactly, excluding navigation/head styling.
    before = original.split('<body>', 1)[1].replace(original_header.group(), '', 1)
    after = updated.split('<body>', 1)[1].replace(shared_header, '', 1)
    if before != after:
        raise ValueError('Published report body unexpectedly changed.')
    target = destination / 'index.html'
    target.write_text(updated)
    for item in source.iterdir():
        if item.is_file() and item.name != 'index.html':
            shutil.copyfile(item, destination / item.name)
    if pdf:
        with tempfile.TemporaryDirectory(prefix='published-pdf-') as tmp:
            pdf_html = Path(tmp) / 'index.html'
            pdf_html.write_text(pdf_compatible_svg(updated))
            for item in source.glob('*.pdf'):
                render_pdf(pdf_html, destination / item.name)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--issue', default='2026-09')
    parser.add_argument('--all', action='store_true', help='Restyle every existing published issue.')
    parser.add_argument('--apply', action='store_true', help='Apply staged, verified presentation files to the publication archive.')
    parser.add_argument('--output-root', type=Path, default=ROOT / 'scratch/review')
    parser.add_argument('--no-pdf', action='store_true')
    args = parser.parse_args()
    if Path(args.issue).name != args.issue or not re.fullmatch(r'\d{4}-\d{2}(?:_(?:3mo|6mo|12mo))?(?:_(?:sale|rent))?', args.issue):
        parser.error('Invalid report issue.')
    sources = sorted(p for p in (ROOT / 'reports').iterdir() if p.is_dir() and (p / 'meta.json').exists()) if args.all else [ROOT / 'reports' / args.issue]
    if args.apply and args.no_pdf:
        parser.error('--apply requires regenerating the PDF too.')
    if args.apply:
        # Build every issue before replacing any archive files. Metadata stays untouched.
        with tempfile.TemporaryDirectory(prefix='restyled-archive-') as tmp:
            staged = Path(tmp)
            for source in sources:
                restyle(source, staged / source.name)
            for source in sources:
                for artifact in (staged / source.name).iterdir():
                    if artifact.name == 'index.html' or artifact.suffix == '.pdf':
                        pending = source / (artifact.name + '.tmp')
                        shutil.copyfile(artifact, pending)
                        pending.replace(source / artifact.name)
                print('Applied presentation:', source.name)
    else:
        for source in sources:
            print(restyle(source, args.output_root / source.name, pdf=not args.no_pdf))


if __name__ == '__main__':
    main()
