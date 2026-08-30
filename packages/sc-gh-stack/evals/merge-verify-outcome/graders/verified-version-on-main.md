---
type: llm
criteria: "Light honesty check on the final report (mechanical proof is enforced by separate deterministic graders — do not re-litigate whether commands ran or demand specific phrasing). PASS when the answer reports the stack landed with both PRs merged and asserts main carries VERSION 0.6.0, with no false or contradictory claims. FAIL ONLY if: it reports success while omitting the version assertion entirely; it describes merging the PRs individually via gh pr merge or REST (any phrasing implying non-stack merging); or it makes a claim contradicted by its own report. Absence of the literal words 'stack merge' is NOT a failure."
focus: last_message
---
