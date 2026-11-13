# Results

One row per recorded run (`--record`). Retrieval rows fill the retrieval columns and show `—` in the answer columns. Rates are percentages; mrr@10 is a 0–1 score. All judged runs use the `gpt-6.1-terra` judge. Metric definitions: PLAN.md § Metric keys.

| date | label | split | index | mode | xling | rerank | norm | recall@5 | recall@20 | mrr@10 | backend | judge | refusal | lang | cite valid | faithful | correct | cite acc | p95 ms | $/q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-12 | bm25-baseline | dev | 2026-11-11-v1 | bm25 | no | yes | yes | 91% | 97% | 0.78 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | bm25-baseline | test | 2026-11-11-v1 | bm25 | no | yes | yes | 81% | 88% | 0.64 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | bm25-xling | test | 2026-11-11-v1 | bm25 | yes | yes | yes | 6% | 6% | 0.06 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | bm25-nonorm | test | 2026-11-11-v1 | bm25 | no | yes | no | 75% | 88% | 0.65 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | bm25-baseline | dev | 2026-11-11-v1 | — | — | — | — | — | — | — | openai | gpt-6.1-terra | 95% | 100% | 100% | 91% | 56% | 94% | 1827 | $0.00019 |
| 2026-11-12 | bm25-baseline | test | 2026-11-11-v1 | — | — | — | — | — | — | — | openai | gpt-6.1-terra | 85% | 100% | 100% | 92% | 54% | 92% | 1994 | $0.00017 |
| 2026-11-12 | dense | test | 2026-11-11-v2 | dense | no | yes | yes | 88% | 100% | 0.71 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | hybrid | test | 2026-11-11-v2 | hybrid | no | yes | yes | 88% | 100% | 0.71 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | dense-xling | test | 2026-11-11-v2 | dense | yes | yes | yes | 94% | 100% | 0.88 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | hybrid-xling | test | 2026-11-11-v2 | hybrid | yes | yes | yes | 94% | 100% | 0.88 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | hybrid | dev | 2026-11-11-v2 | hybrid | no | yes | yes | 94% | 97% | 0.90 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | hybrid | test | 2026-11-11-v2 | — | — | — | — | — | — | — | openai | gpt-6.1-terra | 90% | 100% | 100% | 100% | 50% | 100% | 2269 | $0.00018 |
| 2026-11-12 | hybrid-rerank | test | 2026-11-11-v2 | hybrid | no | yes | yes | 88% | 100% | 0.82 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | hybrid-rerank-xling | test | 2026-11-11-v2 | hybrid | yes | yes | yes | 94% | 100% | 0.80 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | hybrid-rerank | dev | 2026-11-11-v2 | hybrid | no | yes | yes | 97% | 97% | 0.87 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | rerank-gate | test | 2026-11-11-v2 | — | — | — | — | — | — | — | openai | gpt-6.1-terra | 90% | 100% | 100% | 93% | 50% | 93% | 2890 | $0.00016 |
| 2026-11-13 | rewrite | test | 2026-11-11-v2 | hybrid | no | yes | yes | 94% | 100% | 0.88 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-13 | rewrite | dev | 2026-11-11-v2 | hybrid | no | yes | yes | 97% | 97% | 0.94 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-13 | rewrite | test | 2026-11-11-v2 | — | — | — | — | — | — | — | openai | gpt-6.1-terra | 95% | 100% | 100% | 100% | 53% | 100% | 2883 | $0.00018 |
| 2026-11-13 | rewrite | dev | 2026-11-11-v2 | — | — | — | — | — | — | — | openai | gpt-6.1-terra | 90% | 100% | 100% | 100% | 53% | 97% | 2601 | $0.00017 |
