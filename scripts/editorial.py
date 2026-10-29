"""Publication figures and evidence selected deterministically from report metrics."""
from io import StringIO
from html import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

GREEN, AMBER, INK = '#18704d', '#8a5b25', '#222c25'


def money(value):
    if value is None:
        return 'N/A'
    for scale, suffix in ((1e9, 'B'), (1e6, 'M'), (1e3, 'k')):
        if abs(value) >= scale:
            return f'₦{value / scale:,.1f}{suffix}'
    return f'₦{value:,.0f}'


def graphic(fig, label):
    output = StringIO()
    with plt.rc_context({'svg.fonttype': 'path', 'font.family': 'DejaVu Sans', 'font.size': 9}):
        fig.savefig(output, format='svg', bbox_inches='tight', transparent=True, metadata={'Date': None})
    plt.close(fig)
    svg = output.getvalue()
    svg = svg[svg.index('<svg'):]
    return svg.replace('<svg ', f'<svg role="img" aria-label="{escape(label, quote=True)}" ', 1)


def axes_style(ax):
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.spines['bottom'].set_color('#dfdfd5')
    ax.tick_params(length=0, colors=INK, labelsize=9, pad=8)
    ax.grid(axis='x', alpha=.12)
    ax.set_axisbelow(True)


def bars(items, label, colour=GREEN):
    fig, ax = plt.subplots(figsize=(7.4, 2.7))
    if not items:
        ax.text(.5, .5, 'No observations available', ha='center', transform=ax.transAxes)
    else:
        names, values = zip(*items)
        ax.barh(range(len(names)), values, color=colour, height=.48)
        ax.set_yticks(range(len(names)), names)
        ax.invert_yaxis()
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.set_xlim(0, max(values) * 1.22 if max(values) else 1)
        for i, value in enumerate(values):
            ax.text(value, i, f'  {value:,.0f}', va='center', color=INK, fontsize=9)
    axes_style(ax)
    return graphic(fig, label)


def build_publication(metrics):
    publication = {}
    for market in ('sales', 'rentals'):
        data = metrics.get(market)
        if not data:
            continue
        weeks = data['weekly_aggregates']
        classes = sorted(data.get('classes', {}).items(), key=lambda item: item[1]['overall']['cumulative_active_listings'], reverse=True)
        class_counts = [(name.replace('_', ' ').title(), stats['overall']['cumulative_active_listings'] / max(data['overall']['num_weeks'], 1)) for name, stats in classes]
        shown = class_counts[:6]
        if len(class_counts) > 6:
            shown.append(('Other classes', sum(value for _, value in class_counts[6:])))
        figures = {'composition': bars(shown, f'{market.title()} average weekly inventory by property class')}
        fig, ax = plt.subplots(figsize=(7.4, 2.6))
        ax.plot(range(len(weeks)), [w['active_listing_count'] for w in weeks], color=GREEN, marker='o', linewidth=2)
        positions = list(range(0, len(weeks), max(1, len(weeks)//8)))
        if weeks:
            ax.set_xticks(positions, [weeks[i]['week'][5:] for i in positions])
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}'))
        axes_style(ax)
        figures['inventory'] = graphic(fig, f'{market.title()} weekly observed active inventory')
        reductions = data['price_reduction_analysis']
        figures['reductions'] = bars([(r['city'].title(), r['total_reductions']) for r in reductions['by_city'][:6]], f'{market.title()} price reduction event counts by city', AMBER)
        pricing = []
        eligible = [(name, stats) for name, stats in classes if stats['pricing_tiers']['most_expensive'] or stats['pricing_tiers']['most_affordable']][:4]
        for name, stats in eligible:
            tiers = stats['pricing_tiers']
            for kind, key in (('Affordable', 'most_affordable'), ('Expensive', 'most_expensive')):
                for row in tiers[key][:1]:
                    pricing.append(dict(row, property_class=name.replace('_', ' ').title(), tier=kind))
        # Prices stay within class: independent axes avoid a misleading pooled distribution.
        fig, axs = plt.subplots(max(1, len(eligible)), 1, figsize=(7.4, max(2, len(eligible)*1.05)), squeeze=False)
        if not eligible:
            axs[0,0].text(.5,.5,'Insufficient inventory for pricing comparisons',ha='center', transform=axs[0,0].transAxes)
        for ax, (name, stats) in zip(axs[:,0], eligible):
            benchmarks = [(row, colour) for key, colour in (('most_affordable', GREEN), ('most_expensive', AMBER)) for row in stats['pricing_tiers'][key][:1]]
            rows = [row for row, _ in benchmarks]
            rows = [row for row in rows if row['avg_median_price_ngn'] is not None]
            ax.scatter([row['avg_median_price_ngn'] for row in rows], [0]*len(rows), color=[colour for row, colour in benchmarks if row['avg_median_price_ngn'] is not None], s=45)
            ax.set_yticks([])
            ax.set_title(name.replace('_',' ').title(), loc='left', fontsize=9)
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_: money(x)))
            ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
            if rows:
                ax.set_xlim(0, max(row['avg_median_price_ngn'] for row in rows)*1.15 or 1)
            axes_style(ax)
        fig.tight_layout(h_pad=1.8)
        figures['pricing'] = graphic(fig, f'{market.title()} class-specific asking-price benchmarks; independent scales')
        publication[market] = {'figures': figures, 'pricing': pricing, 'classes': classes}
    return publication
