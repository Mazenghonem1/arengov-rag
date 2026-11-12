# Results

One row per recorded run (`--record`). Retrieval rows fill the retrieval columns and show `—` in the answer columns. Rates are percentages; mrr@10 is a 0–1 score. All judged runs use the `gpt-6.1-terra` judge. Metric definitions: PLAN.md § Metric keys.

| date | label | split | index | mode | xling | rerank | norm | recall@5 | recall@20 | mrr@10 | backend | judge | refusal | lang | cite valid | faithful | correct | cite acc | p95 ms | $/q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-12 | bm25-baseline | dev | 2026-11-11-v1 | bm25 | no | yes | yes | 91% | 97% | 0.78 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | bm25-baseline | test | 2026-11-11-v1 | bm25 | no | yes | yes | 81% | 88% | 0.64 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | bm25-xling | test | 2026-11-11-v1 | bm25 | yes | yes | yes | 6% | 6% | 0.06 | — | — | — | — | — | — | — | — | — | — |
| 2026-11-12 | bm25-nonorm | test | 2026-11-11-v1 | bm25 | no | yes | no | 75% | 88% | 0.65 | — | — | — | — | — | — | — | — | — | — |
