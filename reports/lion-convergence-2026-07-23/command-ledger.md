# Research and release command ledger

This ledger records the reproducibility-relevant commands. Generated local-run wrappers, credentials, and secret values are intentionally excluded.

## Orientation and source acquisition

```bash
orx skill
orx skill orx-experiment-tree
orx skill orx-evidence
orx skill orx-git
orx skill orx-compute
orx projects --json
orx project view 55c78d09-4814-4bae-85fa-f0012ab6cba5
orx runs 55c78d09-4814-4bae-85fa-f0012ab6cba5
git rev-parse HEAD
git status --short
git branch -a
df -h .
env | sed 's/=.*//' | sort
curl -L -A 'Mozilla/5.0 (compatible; OpenResearch-Reproduction/1.0; paper-audit)' https://ar5iv.labs.arxiv.org/html/2508.12327
curl -L -A 'Mozilla/5.0 (compatible; OpenResearch-Reproduction/1.0; paper-audit)' https://export.arxiv.org/e-print/2508.12327
```

The live verdict dataset was read at revision `d662bb4753c8fadbfde58ddea3942cd6ec2cc96d` and filtered by the exact key `space_id == "DineshAI/32NvV5zixD"`. The judged Space was downloaded read-only at revision `18c02b05d9b22408040b48f039a35274c1b06d6a`.

## Locked environment

```bash
uv lock
uv sync --frozen
uv run --frozen python -m py_compile repro/src/verify_lion.py
orx project edit 55c78d09-4814-4bae-85fa-f0012ab6cba5 --run-command 'uv run --frozen python repro/src/verify_lion.py'
```

## Experiment tree

```bash
orx create-experiment 55c78d09-4814-4bae-85fa-f0012ab6cba5 --title 'Frozen judged D=10 baseline' --run-command 'uv run --frozen python repro/src/verify_lion.py'
orx exp run c48679ff-51e7-4a39-9f4c-31a16dbc48a0 --backend local
orx exp wait c48679ff-51e7-4a39-9f4c-31a16dbc48a0 --timeout 480
orx logs 4a9a8a0b-4dd6-4133-853c-bb4407bb7b2d

orx create-experiment 55c78d09-4814-4bae-85fa-f0012ab6cba5 --title 'Exact theorem contracts and proof audit' --parent c48679ff-51e7-4a39-9f4c-31a16dbc48a0
orx exp run 9ffb12a2-a640-4743-a185-844d7e09fb9b --backend local
orx exp wait 9ffb12a2-a640-4743-a185-844d7e09fb9b --timeout 480
orx logs 768b7dc1-5835-48f4-afb9-4a8aea082fd9

orx create-experiment 55c78d09-4814-4bae-85fa-f0012ab6cba5 --title 'Multi-axis stochastic rate scaling' --parent c48679ff-51e7-4a39-9f4c-31a16dbc48a0
orx exp run 33a68227-85d3-4588-af63-2a1c633a3f09 --backend local
orx exp wait 33a68227-85d3-4588-af63-2a1c633a3f09 --timeout 480
orx logs 07753634-29f6-4fa7-bc19-b007cee299e9

orx create-experiment 55c78d09-4814-4bae-85fa-f0012ab6cba5 --title 'Cumulative theorem evidence suite' --parent 9ffb12a2-a640-4743-a185-844d7e09fb9b
git merge --no-ff origin/orx/multi-axis-stochastic-rate-scaling
orx exp run b335b7f8-0154-4acf-9f97-33ca9703da3f --backend local
orx exp wait b335b7f8-0154-4acf-9f97-33ca9703da3f --timeout 45
orx logs 80559478-92ff-4975-a448-b07e4bc338d8 --bytes 1000000

orx create-experiment 55c78d09-4814-4bae-85fa-f0012ab6cba5 --title 'Durable cumulative evidence pack' --parent b335b7f8-0154-4acf-9f97-33ca9703da3f
orx exp run e6e0db12-d23b-4d89-8681-ee0b6211dab7 --backend local
orx exp wait e6e0db12-d23b-4d89-8681-ee0b6211dab7 --timeout 45
orx logs 2b1820c4-3447-41f7-8dc7-a5ad276b7590 --bytes 1000000
```

Every node executes the same command:

```bash
uv run --frozen python repro/src/verify_lion.py
```

## Presentation and release validation

```bash
uvx --from marimo marimo check notebooks/lion_claims.py
xmllint --noout reports/lion-convergence-2026-07-23/images/*.svg
rsvg-convert -w 1200 -h 620 reports/lion-convergence-2026-07-23/images/headline-verdicts.svg
git diff --check
git ls-remote origin refs/heads/master
```

The final publication-candidate run and its run ID are recorded in the OpenResearch experiment description and final release report after completion.
