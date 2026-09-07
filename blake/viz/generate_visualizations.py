#!/usr/bin/env python3
"""
Generate comprehensive visualizations for all subdirectories with full annotations.

Moved verbatim from ``scripts/generate_visualizations.py`` (2026-09 scripts
audit): corpus loading, lexical statistics, and matplotlib rendering are
importable/testable logic and belong in ``blake/viz/``. Paths are injected by
the caller (the thin script routes ``data/blake/texts`` and
``analysis_output/visualizations``).
"""
import asyncio
from pathlib import Path
import json
import re
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

# Load corpus
def load_corpus(texts_dir):
    texts_dir = Path(texts_dir)
    works = []
    for txt_file in sorted(texts_dir.glob('*.txt')):
        text = txt_file.read_text(encoding='utf-8', errors='ignore')
        works.append({
            'name': txt_file.stem,
            'title': txt_file.stem.replace('_', ' ').title()[:35],
            'text': text.lower(),
            'words': len(text.split()),
            'chars': len(text),
            'lines': text.count('\n') + 1,
            'sentences': len(re.split(r'[.!?]+', text)),
            'unique_words': len(set(re.findall(r'[a-z]+', text.lower())))
        })
    return works

def stats_box(ax, text, pos='top-right'):
    props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.9, edgecolor='gray')
    positions = {
        'top-right': (0.98, 0.98, 'top', 'right'),
        'top-left': (0.02, 0.98, 'top', 'left'),
        'bottom-right': (0.98, 0.02, 'bottom', 'right'),
        'bottom-left': (0.02, 0.02, 'bottom', 'left')
    }
    x, y, va, ha = positions.get(pos, positions['top-right'])
    ax.text(x, y, text, transform=ax.transAxes, fontsize=9,
            verticalalignment=va, ha=ha, bbox=props, family='monospace')

def generate_text_visualizations(works, output_base):
    output_dir = Path(output_base) / 'text'
    output_dir.mkdir(parents=True, exist_ok=True)

    all_text = ' '.join(w['text'] for w in works)
    plt.style.use('seaborn-v0_8-whitegrid')
    props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.9)

    # 1. Vocabulary Richness
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))

    # TTR
    ax = axes[0, 0]
    ttr = [w['unique_words'] / w['words'] if w['words'] > 0 else 0 for w in works]
    sorted_idx = np.argsort(ttr)[::-1][:15]
    names = [works[i]['title'] for i in sorted_idx]
    values = [ttr[i] for i in sorted_idx]
    ax.barh(names, values, color=plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(names))))
    ax.set_xlabel('Type-Token Ratio', fontsize=11)
    ax.invert_yaxis()
    ax.axvline(np.mean(ttr), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(ttr):.3f}')
    ax.legend()
    ax.set_title('Vocabulary Richness (Type-Token Ratio)', fontsize=12, fontweight='bold')
    stats_box(ax, f'n={len(works)}\nMean={np.mean(ttr):.3f}\nStd={np.std(ttr):.3f}', 'bottom-right')

    # Sentence Length
    ax = axes[0, 1]
    avg_sent = [w['words'] / w['sentences'] if w['sentences'] > 0 else 0 for w in works]
    ax.hist(avg_sent, bins=20, color='steelblue', edgecolor='black', alpha=0.7)
    ax.axvline(np.mean(avg_sent), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(avg_sent):.1f}')
    ax.set_xlabel('Average Words per Sentence', fontsize=11)
    ax.set_ylabel('Number of Works', fontsize=11)
    ax.set_title('Sentence Length Distribution', fontsize=12, fontweight='bold')
    ax.legend()
    if len(avg_sent) >= 3:
        stat, p = stats.shapiro(avg_sent[:50])
        stats_box(ax, f'Shapiro-Wilk\nW={stat:.4f}\np={p:.4f}', 'top-right')

    # Word Count vs Unique
    ax = axes[1, 0]
    word_counts = [w['words'] for w in works]
    unique_counts = [w['unique_words'] for w in works]
    ax.scatter(word_counts, unique_counts, alpha=0.7, s=80, c=range(len(works)), cmap='viridis', edgecolors='black')
    slope, intercept, r_value, p_value, _ = stats.linregress(word_counts, unique_counts)
    x_line = np.linspace(min(word_counts), max(word_counts), 100)
    ax.plot(x_line, slope*x_line + intercept, 'r-', linewidth=2, label=f'R²={r_value**2:.3f}')
    ax.set_xlabel('Total Word Count', fontsize=11)
    ax.set_ylabel('Unique Words', fontsize=11)
    ax.set_title('Word Count vs Vocabulary Size', fontsize=12, fontweight='bold')
    ax.legend()
    stats_box(ax, f'Linear Regression\nSlope={slope:.4f}\nR²={r_value**2:.4f}\np={p_value:.2e}', 'top-left')

    # Lexical Density
    ax = axes[1, 1]
    content_words = ['heaven', 'hell', 'love', 'death', 'soul', 'god', 'angel', 'vision', 'fire', 'water']
    lex_density = [sum(w['text'].count(cw) for cw in content_words) / w['words'] * 100 if w['words'] > 0 else 0 for w in works]
    sorted_idx = np.argsort(lex_density)[::-1][:15]
    names = [works[i]['title'] for i in sorted_idx]
    values = [lex_density[i] for i in sorted_idx]
    ax.barh(names, values, color=plt.cm.plasma(np.linspace(0.2, 0.8, len(names))))
    ax.set_xlabel('Lexical Density (%)', fontsize=11)
    ax.invert_yaxis()
    ax.set_title('Lexical Density (Key Terms %)', fontsize=12, fontweight='bold')
    stats_box(ax, f'Mean={np.mean(lex_density):.2f}%\nBased on {len(content_words)} terms', 'bottom-right')

    plt.suptitle('TEXT ANALYSIS: Vocabulary & Linguistic Features', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'vocabulary_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('   ✅ text/vocabulary_analysis.png')

    # 2. Zipf's Law
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    all_words = re.findall(r'[a-z]+', all_text)
    word_freq = Counter(all_words)
    sorted_freq = sorted(word_freq.values(), reverse=True)

    ax = axes[0]
    ranks = range(1, len(sorted_freq) + 1)
    ax.loglog(ranks, sorted_freq, 'b-', alpha=0.5, linewidth=0.5)
    ax.loglog(ranks[:1000], sorted_freq[:1000], 'r-', linewidth=2, label='Top 1000')
    log_ranks = np.log(list(ranks[:500]))
    log_freqs = np.log(sorted_freq[:500])
    slope, intercept, r_value, _, _ = stats.linregress(log_ranks, log_freqs)
    ax.set_xlabel('Rank (log)', fontsize=11)
    ax.set_ylabel('Frequency (log)', fontsize=11)
    ax.set_title("Zipf's Law Analysis", fontsize=12, fontweight='bold')
    ax.legend()
    stats_box(ax, f"Zipf's Law\nα={-slope:.3f}\nR²={r_value**2:.4f}\nExpected α≈1.0", 'top-right')

    ax = axes[1]
    stopwords = {'the', 'and', 'of', 'to', 'in', 'a', 'is', 'that', 'for', 'with', 'as', 'his',
                 'was', 'he', 'be', 'on', 'are', 'by', 'i', 'this', 'thy', 'thee', 'thou'}
    content_freq = {w: c for w, c in word_freq.items() if w not in stopwords and len(w) > 2}
    top_30 = sorted(content_freq.items(), key=lambda x: x[1], reverse=True)[:30]
    ax.barh([w[0] for w in top_30], [w[1] for w in top_30],
            color=plt.cm.viridis(np.linspace(0, 0.8, 30)))
    ax.set_xlabel('Frequency', fontsize=11)
    ax.invert_yaxis()
    ax.set_title('Top 30 Content Words', fontsize=12, fontweight='bold')

    plt.suptitle('TEXT ANALYSIS: Word Frequency Distribution', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'word_frequency_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('   ✅ text/word_frequency_analysis.png')

    # 3. Readability
    fig, ax = plt.subplots(figsize=(14, 12))
    readability = []
    for w in works:
        avg_sent_len = w['words'] / max(w['sentences'], 1)
        avg_word_len = w['chars'] / max(w['words'], 1)
        score = 206.835 - 1.015 * avg_sent_len - 84.6 * (avg_word_len / 5)
        readability.append(max(0, min(100, score)))

    sorted_idx = np.argsort(readability)
    names = [works[i]['title'] for i in sorted_idx]
    scores = [readability[i] for i in sorted_idx]
    ax.barh(names, scores, color=plt.cm.RdYlGn(np.array(scores) / 100))
    ax.axvline(np.mean(scores), color='blue', linestyle='--', linewidth=2, label=f'Mean: {np.mean(scores):.1f}')
    ax.set_xlabel('Readability Score', fontsize=11)
    ax.set_title('Readability Analysis (Flesch-Kincaid)', fontsize=14, fontweight='bold')
    ax.legend()

    interpret = '90-100: Very Easy\n80-89: Easy\n70-79: Fairly Easy\n60-69: Standard\n50-59: Fairly Difficult\n30-49: Difficult\n0-29: Very Difficult'
    ax.text(1.02, 0.5, interpret, transform=ax.transAxes, fontsize=10, va='center', bbox=props)
    plt.tight_layout()
    plt.savefig(output_dir / 'readability_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('   ✅ text/readability_analysis.png')

def generate_temporal_visualizations(works, output_base):
    output_dir = Path(output_base) / 'temporal'
    output_dir.mkdir(parents=True, exist_ok=True)
    props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.9)

    # Sort by word count as proxy for chronology (larger works tend to be later)
    sorted_works = sorted(works, key=lambda w: w['words'])

    fig, axes = plt.subplots(2, 2, figsize=(16, 14))

    # Cumulative corpus growth
    ax = axes[0, 0]
    cumulative = np.cumsum([w['words'] for w in sorted_works])
    ax.fill_between(range(len(sorted_works)), cumulative, alpha=0.3, color='steelblue')
    ax.plot(range(len(sorted_works)), cumulative, 'b-', linewidth=2)
    ax.scatter(range(len(sorted_works)), cumulative, s=30, c='navy', zorder=5)
    ax.set_xlabel('Work Index (by size)', fontsize=11)
    ax.set_ylabel('Cumulative Word Count', fontsize=11)
    ax.set_title('Corpus Growth by Work Size', fontsize=12, fontweight='bold')
    stats_box(ax, f'Total: {cumulative[-1]:,} words\n{len(works)} works', 'top-left')

    # Work sizes over index
    ax = axes[0, 1]
    sizes = [w['words'] for w in sorted_works]
    ax.bar(range(len(sorted_works)), sizes, color=plt.cm.viridis(np.linspace(0, 1, len(sizes))))
    ax.set_xlabel('Work Index', fontsize=11)
    ax.set_ylabel('Word Count', fontsize=11)
    ax.set_title('Work Sizes Distribution', fontsize=12, fontweight='bold')
    stats_box(ax, f'Mean: {np.mean(sizes):,.0f}\nMedian: {np.median(sizes):,.0f}\nStd: {np.std(sizes):,.0f}', 'top-right')

    # Theme evolution across corpus
    ax = axes[1, 0]
    themes = {
        'Innocence': ['innocent', 'innocence', 'child', 'lamb', 'joy'],
        'Experience': ['experience', 'woe', 'sorrow', 'weep'],
        'Spiritual': ['heaven', 'god', 'angel', 'divine'],
        'Mythology': ['urizen', 'los', 'albion', 'orc']
    }
    for theme_name, keywords in themes.items():
        theme_counts = []
        for w in sorted_works:
            count = sum(w['text'].count(kw) for kw in keywords)
            norm_count = count / w['words'] * 1000 if w['words'] > 0 else 0
            theme_counts.append(norm_count)
        ax.plot(range(len(sorted_works)), theme_counts, label=theme_name, linewidth=2, alpha=0.8)
    ax.set_xlabel('Work Index (by size)', fontsize=11)
    ax.set_ylabel('Theme Density (per 1000 words)', fontsize=11)
    ax.set_title('Theme Evolution Across Corpus', fontsize=12, fontweight='bold')
    ax.legend()

    # Vocabulary evolution
    ax = axes[1, 1]
    ttr_evolution = [w['unique_words'] / w['words'] if w['words'] > 0 else 0 for w in sorted_works]
    ax.scatter(range(len(sorted_works)), ttr_evolution, c=range(len(sorted_works)), cmap='plasma', s=60, edgecolors='black')
    z = np.polyfit(range(len(sorted_works)), ttr_evolution, 1)
    p = np.poly1d(z)
    ax.plot(range(len(sorted_works)), p(range(len(sorted_works))), 'r--', linewidth=2, label=f'Trend (slope={z[0]:.4f})')
    ax.set_xlabel('Work Index', fontsize=11)
    ax.set_ylabel('Type-Token Ratio', fontsize=11)
    ax.set_title('Vocabulary Richness Evolution', fontsize=12, fontweight='bold')
    ax.legend()

    plt.suptitle('TEMPORAL ANALYSIS: Corpus Evolution', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'temporal_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('   ✅ temporal/temporal_analysis.png')

def generate_network_visualizations(works, output_base):
    output_dir = Path(output_base) / 'network'
    output_dir.mkdir(parents=True, exist_ok=True)

    all_text = ' '.join(w['text'] for w in works)
    props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.9)

    # Term co-occurrence correlation
    terms = ['heaven', 'hell', 'love', 'death', 'joy', 'sorrow', 'vision', 'reason',
             'angel', 'devil', 'soul', 'body', 'fire', 'water', 'sun', 'moon',
             'god', 'eternity', 'innocence', 'experience']

    term_vectors = {t: [] for t in terms}
    for w in works:
        for t in terms:
            term_vectors[t].append(w['text'].count(t))

    # Correlation matrix
    n = len(terms)
    corr_matrix = np.zeros((n, n))
    for i, t1 in enumerate(terms):
        for j, t2 in enumerate(terms):
            v1, v2 = np.array(term_vectors[t1]), np.array(term_vectors[t2])
            if np.std(v1) > 0 and np.std(v2) > 0:
                corr_matrix[i,j] = np.corrcoef(v1, v2)[0,1]

    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    # Heatmap
    ax = axes[0]
    im = ax.imshow(corr_matrix, cmap='RdBu', vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_xticklabels([t.capitalize() for t in terms], rotation=45, ha='right', fontsize=9)
    ax.set_yticks(range(n))
    ax.set_yticklabels([t.capitalize() for t in terms], fontsize=9)
    ax.set_title('Term Co-occurrence Correlation Matrix', fontsize=12, fontweight='bold')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Pearson Correlation', fontsize=10)

    # Top correlations
    ax = axes[1]
    correlations = []
    for i in range(n):
        for j in range(i+1, n):
            correlations.append((terms[i], terms[j], corr_matrix[i,j]))
    correlations.sort(key=lambda x: abs(x[2]), reverse=True)
    top_20 = correlations[:20]

    labels = [f'{c[0]}-{c[1]}' for c in top_20]
    values = [c[2] for c in top_20]
    colors = ['green' if v > 0 else 'red' for v in values]
    ax.barh(labels, values, color=colors, alpha=0.7)
    ax.axvline(0, color='black', linewidth=1)
    ax.set_xlabel('Correlation', fontsize=11)
    ax.set_title('Top 20 Term Pair Correlations', fontsize=12, fontweight='bold')
    ax.invert_yaxis()
    stats_box(ax, f'{len(terms)} terms analyzed\n{len(correlations)} pairs\ndescriptive |r| ranking\nno inferential p-values', 'bottom-right')

    plt.suptitle('NETWORK ANALYSIS: Term Relationships', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'network_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('   ✅ network/network_analysis.png')

def generate_comparative_visualizations(works, output_base):
    output_dir = Path(output_base) / 'comparative'
    output_dir.mkdir(parents=True, exist_ok=True)
    props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.9)

    # Compare top works
    top_works = sorted(works, key=lambda w: w['words'], reverse=True)[:10]

    fig, axes = plt.subplots(2, 2, figsize=(16, 14))

    # Word count comparison
    ax = axes[0, 0]
    names = [w['title'] for w in top_works]
    word_counts = [w['words'] for w in top_works]
    ax.barh(names, word_counts, color=plt.cm.Set2(range(10)))
    ax.set_xlabel('Word Count', fontsize=11)
    ax.set_title('Top 10 Works by Size', fontsize=12, fontweight='bold')
    ax.invert_yaxis()
    for i, v in enumerate(word_counts):
        ax.text(v + 1000, i, f'{v:,}', va='center', fontsize=9)

    # Vocabulary comparison
    ax = axes[0, 1]
    unique_counts = [w['unique_words'] for w in top_works]
    ax.barh(names, unique_counts, color=plt.cm.Pastel1(range(10)))
    ax.set_xlabel('Unique Words', fontsize=11)
    ax.set_title('Vocabulary Size Comparison', fontsize=12, fontweight='bold')
    ax.invert_yaxis()

    # Theme comparison
    ax = axes[1, 0]
    themes = ['heaven', 'hell', 'love', 'soul', 'vision']
    x = np.arange(len(top_works))
    width = 0.15
    for i, theme in enumerate(themes):
        counts = [w['text'].count(theme) for w in top_works]
        ax.bar(x + i*width, counts, width, label=theme.capitalize())
    ax.set_xticks(x + width*2)
    ax.set_xticklabels([w['title'][:15] for w in top_works], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Occurrences', fontsize=11)
    ax.set_title('Theme Distribution Across Works', fontsize=12, fontweight='bold')
    ax.legend()

    # Sentence structure comparison
    ax = axes[1, 1]
    avg_sentence = [w['words'] / max(w['sentences'], 1) for w in top_works]
    ax.bar(range(len(top_works)), avg_sentence, color=plt.cm.coolwarm(np.linspace(0.2, 0.8, len(top_works))))
    ax.set_xticks(range(len(top_works)))
    ax.set_xticklabels([w['title'][:12] for w in top_works], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Avg Words/Sentence', fontsize=11)
    ax.set_title('Sentence Complexity Comparison', fontsize=12, fontweight='bold')
    ax.axhline(np.mean(avg_sentence), color='red', linestyle='--', label=f'Mean: {np.mean(avg_sentence):.1f}')
    ax.legend()

    plt.suptitle('COMPARATIVE ANALYSIS: Major Works', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'comparative_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('   ✅ comparative/comparative_analysis.png')

def generate_image_visualizations(works, output_base):
    output_dir = Path(output_base) / 'image'
    output_dir.mkdir(parents=True, exist_ok=True)

    all_text = ' '.join(w['text'] for w in works)
    props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.9)

    # Visual imagery terms
    colors_terms = {'red': all_text.count('red'), 'blue': all_text.count('blue'),
                    'gold': all_text.count('gold'), 'white': all_text.count('white'),
                    'black': all_text.count('black'), 'green': all_text.count('green'),
                    'silver': all_text.count('silver'), 'purple': all_text.count('purple')}

    light_terms = {'light': all_text.count('light'), 'dark': all_text.count('dark'),
                   'bright': all_text.count('bright'), 'shadow': all_text.count('shadow'),
                   'sun': all_text.count('sun'), 'moon': all_text.count('moon'),
                   'star': all_text.count('star'), 'flame': all_text.count('flame')}

    fig, axes = plt.subplots(2, 2, figsize=(16, 14))

    # Color vocabulary
    ax = axes[0, 0]
    sorted_colors = sorted(colors_terms.items(), key=lambda x: x[1], reverse=True)
    color_names = [c[0] for c in sorted_colors]
    color_counts = [c[1] for c in sorted_colors]
    actual_colors = ['red', 'blue', 'gold', 'white', 'black', 'green', 'silver', 'purple']
    bar_colors = [c if c in actual_colors else 'gray' for c in color_names]
    ax.bar(color_names, color_counts, color=bar_colors, edgecolor='black')
    ax.set_ylabel('Frequency', fontsize=11)
    ax.set_title('Color Vocabulary in Blake', fontsize=12, fontweight='bold')
    stats_box(ax, f'Total color words: {sum(color_counts):,}', 'top-right')

    # Light/Dark imagery
    ax = axes[0, 1]
    sorted_light = sorted(light_terms.items(), key=lambda x: x[1], reverse=True)
    ax.barh([l[0] for l in sorted_light], [l[1] for l in sorted_light],
            color=plt.cm.YlOrRd(np.linspace(0.2, 0.8, len(sorted_light))))
    ax.set_xlabel('Frequency', fontsize=11)
    ax.set_title('Light/Dark Imagery', fontsize=12, fontweight='bold')
    ax.invert_yaxis()

    # Light vs Dark ratio
    ax = axes[1, 0]
    light_count = sum(all_text.count(t) for t in ['light', 'bright', 'sun', 'star', 'radiant'])
    dark_count = sum(all_text.count(t) for t in ['dark', 'shadow', 'night', 'black', 'gloom'])
    ax.pie([light_count, dark_count], labels=['Light', 'Dark'],
           colors=['gold', 'dimgray'], autopct='%1.1f%%', explode=(0.05, 0.05),
           shadow=True, startangle=90)
    ax.set_title('Light vs Dark Balance', fontsize=12, fontweight='bold')

    # Visual descriptors
    ax = axes[1, 1]
    visual_terms = {'beautiful': all_text.count('beautiful'), 'terrible': all_text.count('terrible'),
                    'vast': all_text.count('vast'), 'small': all_text.count('small'),
                    'bright': all_text.count('bright'), 'dim': all_text.count('dim'),
                    'ancient': all_text.count('ancient'), 'new': all_text.count('new')}
    sorted_visual = sorted(visual_terms.items(), key=lambda x: x[1], reverse=True)
    ax.bar([v[0] for v in sorted_visual], [v[1] for v in sorted_visual],
           color=plt.cm.Spectral(np.linspace(0.1, 0.9, len(sorted_visual))))
    ax.set_ylabel('Frequency', fontsize=11)
    ax.set_title('Visual Descriptors', fontsize=12, fontweight='bold')
    plt.xticks(rotation=45, ha='right')

    plt.suptitle('IMAGE ANALYSIS: Visual Vocabulary & Imagery', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'image_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('   ✅ image/image_analysis.png')

def generate_all_visualizations(texts_dir, output_base):
    print('=' * 80)
    print('COMPREHENSIVE VISUALIZATION GENERATION')
    print('=' * 80)

    works = load_corpus(texts_dir)
    print(f'\nLoaded {len(works)} works')

    print('\n📊 Generating TEXT visualizations...')
    generate_text_visualizations(works, output_base)

    print('\n📊 Generating TEMPORAL visualizations...')
    generate_temporal_visualizations(works, output_base)

    print('\n📊 Generating NETWORK visualizations...')
    generate_network_visualizations(works, output_base)

    print('\n📊 Generating COMPARATIVE visualizations...')
    generate_comparative_visualizations(works, output_base)

    print('\n📊 Generating IMAGE visualizations...')
    generate_image_visualizations(works, output_base)

    print('\n' + '=' * 80)
    print('✅ ALL SUBDIRECTORY VISUALIZATIONS COMPLETE')
    print('=' * 80)

    # List all generated files
    base_dir = Path(output_base)
    for subdir in ['text', 'temporal', 'network', 'comparative', 'image']:
        subdir_path = base_dir / subdir
        if subdir_path.exists():
            files = list(subdir_path.glob('*.png'))
            print(f'\n{subdir}/:')
            for f in files:
                print(f'   - {f.name} ({f.stat().st_size:,} bytes)')
