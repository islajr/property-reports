"""Decision-oriented comparisons from the exact source cohort used by metrics."""
import hashlib
from pathlib import Path
from compute_metrics import load_snapshots


def build_research(metrics, csv_path):
    path = Path(csv_path)
    expected = metrics.get('_source', {}).get('csv_sha256')
    if not expected or not path.exists():
        return {}
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Research CSV differs from the source used to compute these metrics.')
    df = load_snapshots(path)
    result = {}
    for market, price_type in (('sales', 'FOR_SALE'), ('rentals', 'FOR_RENT')):
        data = metrics.get(market)
        if not data:
            continue
        weeks = data['overall']['weeks']
        sample = df[(df.price_type == price_type) & df.snapshot_week.astype(str).isin(weeks)]
        total = int(sample.active_listing_count.sum())
        cities = []
        comparisons = []
        for (city, prop_class, hood), group in sample.groupby(['city', 'property_class', 'neighbourhood']):
            weekly = group.groupby('snapshot_week').active_listing_count.sum()
            priced = group[group.median_price_kobo.notna()]
            if weekly.mean() < 3 or priced.empty:
                continue
            comparisons.append({'city': city, 'class_key': prop_class, 'property_class': prop_class.replace('_', ' ').title(),
                'neighbourhood': hood, 'price': float(priced.median_price_kobo.mean()) / 100,
                'weeks': int(group.snapshot_week.nunique()), 'priced_weeks': int(priced.snapshot_week.nunique()),
                'active': round(float(weekly.mean()), 1)})
        for city, group in sample.groupby('city'):
            count = int(group.active_listing_count.sum())
            classes = group.groupby('property_class').active_listing_count.sum().sort_values(ascending=False)
            city_rows = sorted([row for row in comparisons if row['city'] == city], key=lambda row: (-row['active'], row['neighbourhood']))
            cities.append({'city': city, 'listing_weeks': count, 'share': count/total*100 if total else 0,
                'average_active': round(count/max(len(weeks), 1), 1), 'new': int(group.new_listings_count.sum()),
                'reductions': int(group.price_reduced_count.sum()), 'areas': int(group.neighbourhood.nunique()),
                'leading_class': str(classes.index[0]).replace('_', ' ').title() if not classes.empty else 'N/A',
                'leading_class_share': round(float(classes.iloc[0])/count*100, 1) if count else 0,
                'benchmarks': city_rows[:8]})
        cities.sort(key=lambda row: (-row['listing_weeks'], row['city']))
        class_totals = sample.groupby('property_class').active_listing_count.sum().sort_values(ascending=False)
        books = []
        for prop_class in class_totals.index[:4]:
            rows = sorted([row for row in comparisons if row['class_key'] == prop_class], key=lambda row: (-row['active'], row['city'], row['neighbourhood']))[:10]
            rows.sort(key=lambda row: (row['city'], row['price']))
            if rows:
                books.append({'name': prop_class.replace('_', ' ').title(), 'rows': rows,
                    'lowest': min(rows, key=lambda row: row['price']),
                    'highest': max(rows, key=lambda row: row['price'])})
        result[market] = {'cities': cities, 'briefs': cities[:2], 'other_cities': cities[2:], 'price_books': books,
            'all_comparisons': comparisons, 'top_two_share': round(sum(city['listing_weeks'] for city in cities[:2])/total*100, 1) if total else 0,
            'total_listing_weeks': total, 'report_weeks': len(weeks)}
    return result


def comparison_download(research):
    """Use explicit units in the public aggregate file; protect spreadsheet text cells."""
    def text_cell(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value

    return [{
        'market': market,
        'city': text_cell(row['city']),
        'neighbourhood': text_cell(row['neighbourhood']),
        'property_class': text_cell(row['class_key']),
        'mean_group_median_ngn': row['price'],
        'rental_period': 'year_assumed' if market == 'rentals' else 'not_applicable',
        'average_active_per_observed_week': row['active'],
        'observed_weeks': row['weeks'],
        'priced_weeks': row['priced_weeks'],
        'report_weeks': study['report_weeks'],
    } for market, study in research.items() for row in study['all_comparisons']]


def research_provenance(metrics, research):
    return {
        'source_csv_sha256': metrics['_source']['csv_sha256'],
        'coverage_quality': metrics.get('quality', {}),
        'included_week_starts': {market: metrics[market]['overall']['weeks'] for market in research},
        'eligibility': 'At least 3 average active listings per observed week and at least one usable group median.',
        'print_selection': 'Four largest classes by listing-weeks; up to ten eligible areas per class selected by average observed inventory, ordered by city and price.',
        'definitions': {
            'mean_group_median_ngn': 'Unweighted mean of usable weekly area/class group medians, converted from kobo to NGN. Not a pooled listing-level median or valuation.',
            'average_active_per_observed_week': 'Summed active listing counts divided by weeks observed for this area/class; rounded to one decimal.',
            'observed_weeks': 'Distinct week starts with a source row for this area/class.',
            'priced_weeks': 'Distinct week starts with a usable positive finite median price.',
            'report_weeks': 'Included week starts for the whole market, after the metrics coverage filter.',
            'listing_weeks': 'Sum of weekly active counts; properties may recur in several weeks.',
            'rental_period': 'Annual asking rents are assumed from the source, not independently verified.',
        },
        'limitations': ['Reconstructed historical prices reuse current listing records.',
                        'Broad classes do not control for size, bedrooms, condition or tenure.',
                        'Portal coverage is not representative of national stock or completed transactions.'],
        'spreadsheet_text': 'Potential formula text is prefixed with an apostrophe in CSV downloads.',
    }
