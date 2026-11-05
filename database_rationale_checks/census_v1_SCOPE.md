# Saved-output census scope

The census covers exactly the flat, keyed `lite`, `verified`, and
`verified_negctrl` cohorts under `historical_analysis/data/llm_reviews/`.
The separately nested `agents` and `human_subset` directories are outside this
inventory. It is not an inventory of every file or experiment in the project.

There are 7,011 saved output records with matching packet keys: 3,731 accepted,
3,262 nonaccepted and 18 explicit parse-failure records. The historical loader
already excludes null decisions from valid verdicts; these 18 are not newly
discovered model misjudgments and do not change the existing historical rates.

The 221 absent key/reviewer positions all belong to the hosted negative cohort:
302 available packet keys minus 81 saved outputs. This is not 221 proven failed
requests. The historical script selected only a smaller execution subset, whose
one unexplained missing position was already documented. Do not confuse the
candidate pool with the historical intended-call denominator.

Repeated tasks across splits, reviewers, and prompt conditions remain separate
output records. Neither 7,011 nor 3,262 is a count of independent tasks. The
nonaccepted worklist is a navigation and adjudication preparation file. Its
unadjudicated statuses must not be converted into accuracy or hallucination rates.

The hosted Verified/negative cohorts contain 30 nonaccepted resolved-agent cases,
3 gold cases and 38 failing-agent cases (71 records), matching the earlier
deterministic six-case selection frame. The new SQLite integration checks concern
one of those gold cases and one failing-agent case; they do not adjudicate all 71.
