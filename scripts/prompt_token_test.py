import json
from pathlib import Path
from app.prompt import build_prompt, aggregate_by_category
import tiktoken


def load_sample(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


if __name__ == '__main__':
    # expect sample files under scripts/samples/*.json
    samples_dir = Path(__file__).parent / 'samples'
    samples = list(samples_dir.glob('*.json'))
    if not samples:
        print('No samples found in scripts/samples. Create at least two sample files.')
        raise SystemExit(1)

    results = {}
    for s in samples:
        data = load_sample(s)
        full_prompt = build_prompt(data, mode='full')
        agg_prompt = build_prompt(data, mode='aggregated')
        results[s.name] = {
            'full_tokens': count_tokens(full_prompt),
            'agg_tokens': count_tokens(agg_prompt),
            'transactions_count': len(data),
        }

    print(json.dumps(results, ensure_ascii=False, indent=2))
