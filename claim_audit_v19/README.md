# ICSE #6658 v19: claim checks and stored-rationale limits

The ten-page manuscript now discloses that the historical normalizer caps each summary and issue description at 600 characters and does not retain successful raw response text. The original study and older releases are unchanged.

An independent standard-library implementation reconstructs acceptance as decision=merge with no blocking issue. All 6,993 valid verdicts among 7,011 primary Lite/Verified/Verified-negative files match. Eighteen excluded outputs are not rejections. An additional 2,245 scaffold/human-subset files also match; those include overlaps and are counted separately.

In the primary panels, 225 summaries and 12 issue descriptions reach the cap, across 232 verdicts. Exactly 600 characters identifies a storage boundary, not proof that every such field lost text. These limits constrain rationale audits. They do not change stored decision/severity or prove the factual truth of a rationale. Forty-two primary outputs say merge but contain a blocker and are correctly treated as nonaccepted by the defined metric.

All 128 metric comparisons and nine normalizer boundary checks pass. Independently reconstructed statistics are Pearson r=.9938298744 across ten open model/prompt configurations, Fleiss kappa=.0244808566 across five adjusted reviewers on 383 common packets, and hosted acceptance 164/194 agent versus 191/194 gold, discordants29/2, exact McNemar p=4.6286732e-7. These are exploratory statistics, not maintainer validation.

All 114 retained JSON/JUnit result files for the selected 38 failing cases were hash-checked and recounted:447 executed slots, zero skips, developer controls passing. These are prior executions, not114 newly run experiments. Functional evidence does not adjudicate every rationale sentence.

The PDF remains10 pages, references start on10, with22 embedded fonts. Layout, historical numeric inputs, bibliography, figures and tables are unchanged. No new inference, human response, functional experiment or GPU job is added. Human independence, native prior-system conditions and exact historical hosted identity remain unresolved. No conference submission or publisher certification is claimed. Private reviewer text and author-only session logs are excluded.

## Reproduce the new stored-output audit

From the repository root, with Python3.10+ and no extra packages:

    python claim_audit_v19/tools/audit_normalized_verdicts.py --study historical_analysis --census reverse_audit_v18/evidence/rationale_census_v18.json --out /tmp/icse6658-v19-recheck.json

The output path must not already exist. This was replayed against the retained anonymously downloaded historical archive, producing the identical result object. It requires the existing historical_analysis and reverse_audit_v18 trees. It does not contact model APIs. The separate source ZIP rebuilds the paper with IEEEtran/BibTeX or cached Tectonic.
