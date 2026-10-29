"""Preview typography/layout changes while preserving the published report body."""
import argparse
from pathlib import Path
import re
import shutil
from jinja2 import Environment, FileSystemLoader
from render_report import build_embedded_fonts_css, render_pdf

ROOT = Path(__file__).resolve().parents[1]


def restyle(source, destination, pdf=True):
    if destination.resolve() == (ROOT / 'reports').resolve() or (ROOT / 'reports').resolve() in destination.resolve().parents:
        raise ValueError('Presentation review output must be outside the published archive.')
    destination.mkdir(parents=True, exist_ok=True)
    original = (source / 'index.html').read_text()
    # The old site header is the only removed body markup. Report prose is untouched.
    original_header = re.search(r'<header class="global-header">.*?</header>', original, re.S)
    if not original_header:
        raise ValueError('Expected the original published report header.')
    env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=True)
    shared_header = env.get_template('partials/header.html.j2').render()
    css = (ROOT / 'templates/partials/site.css').read_text() + (ROOT / 'templates/partials/published-report.css').read_text()
    style = '<style id="publication-presentation">' + build_embedded_fonts_css() + css + '</style>'
    script = '<script>' + (ROOT / 'templates/partials/theme.js').read_text() + '</script>'
    updated = original.replace('</head>', style + script + '</head>', 1).replace(original_header.group(), shared_header, 1)
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
        for item in source.glob('*.pdf'):
            render_pdf(target, destination / item.name)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--issue', default='2026-09')
    parser.add_argument('--output-root', type=Path, default=ROOT / 'scratch/review')
    parser.add_argument('--no-pdf', action='store_true')
    args = parser.parse_args()
    if Path(args.issue).name != args.issue or not re.fullmatch(r'\d{4}-\d{2}(?:_(?:3mo|6mo|12mo))?(?:_(?:sale|rent))?', args.issue):
        parser.error('Invalid report issue.')
    print(restyle(ROOT / 'reports' / args.issue, args.output_root / args.issue, pdf=not args.no_pdf))


if __name__ == '__main__':
    main()
