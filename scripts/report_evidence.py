"""Shared, auditable facts for narrative prompts, charts and benchmark tables."""
import re


def money(value):
    if value is None:
        return 'N/A'
    for scale, suffix in ((1e9, 'B'), (1e6, 'M'), (1e3, 'k')):
        if abs(value) >= scale:
            return f'₦{value / scale:,.1f}{suffix}'
    return f'₦{value:,.0f}'


def selected_classes(data):
    return sorted(data.get('classes', {}).items(), key=lambda pair: (-pair[1]['overall']['cumulative_active_listings'], pair[0]))


def pricing_benchmarks(data):
    eligible = [(name, stats) for name, stats in selected_classes(data) if any(stats['pricing_tiers'][key] for key in ('most_affordable', 'most_expensive'))][:4]
    rows = []
    for name, stats in eligible:
        for tier, key in (('Affordable', 'most_affordable'), ('Expensive', 'most_expensive')):
            for row in stats['pricing_tiers'][key][:1]:
                rows.append(dict(row, class_key=name, property_class=name.replace('_', ' ').title(), tier=tier))
    return eligible, rows


def numeric_tokens(text):
    return {value.replace(',', '') for value in re.findall(r'\d[\d,]*(?:\.\d+)?(?:[BMk%])?', text)}


def evidence_for_market(data, market):
    ov = data['overall']
    facts = {}
    def add(key, text):
        facts[key] = text
    add('inventory.peak', f"Peak observed {market} inventory was {ov['peak_active_listings']:,} active listings across {ov['num_weeks']} included weeks.")
    add('inventory.new', f"{ov['total_new_listings']:,} {market} listings were first discovered in the included weeks.")
    add('inventory.coverage', f"Observations cover {ov['num_cities']} cities and {ov['unique_neighbourhoods']} city/neighbourhood pairs.")
    for i, row in enumerate(data['inventory_ranking'][:3]):
        add(f'inventory.area.{i}', f"{row['neighbourhood']} ({row['city']}) averaged {row['avg_weekly_active_listings']:,.1f} active listings per observed week.")
    _, rows = pricing_benchmarks(data)
    for i, row in enumerate(rows):
        sample = ''
        if 'avg_weekly_active_listings' in row:
            sample = f" Coverage: {row['num_weeks_observed']} observed weeks; {row['avg_weekly_active_listings']:,.1f} average weekly active listings."
        add(f'pricing.area.{i}', f"{row['property_class']}: {row['tier'].lower()} benchmark {row['neighbourhood']} ({row['city']}) has a mean observed group median of {money(row['avg_median_price_ngn'])}{'/yr' if market == 'rentals' else ''}.{sample}")
    add('pricing.limit', 'Benchmarks compare areas within property classes. They are advertised asking prices, not transaction prices or an appreciation history. Independent chart scales must not be compared as one pooled distribution.')
    reductions = data['price_reduction_analysis']
    add('reductions.total', f"{reductions['total_price_reductions']:,} asking-price reduction events were recorded in the {market} market.")
    for i, row in enumerate(reductions['by_city'][:3]):
        add(f'reductions.city.{i}', f"{row['city']} accounts for {row['total_reductions']:,} recorded reduction events.")
    add('reductions.limit', 'These are event counts, not discount rates or unique listings. More than one event can occur on a listing; market size and observation coverage affect counts.')
    return facts


def takeaways(data, market):
    ov = data['overall']
    return [f"Peak observed {market} inventory: {ov['peak_active_listings']:,} active listings.",
            f"{ov['total_new_listings']:,} listings first discovered during the included weeks.",
            f"{ov['total_price_reductions']:,} asking-price reduction events recorded."]


def evidence_narrative(metrics):
    result = {'_quality_version': 2}
    for market in ('sales', 'rentals'):
        data = metrics.get(market)
        if not data:
            result[market] = None
            continue
        facts = evidence_for_market(data, market)
        refs = {'inventory_narrative': ['inventory.peak', 'inventory.coverage'],
                'pricing_narrative': ['pricing.limit'],
                'price_reduction_narrative': ['reductions.total', 'reductions.limit']}
        result[market] = {field: ' '.join(facts[key] for key in keys) for field, keys in refs.items()}
        result[market]['evidence_refs'] = refs
        result[market]['key_takeaways'] = takeaways(data, market)
    return result
