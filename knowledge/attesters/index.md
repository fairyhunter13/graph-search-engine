# Attesters

`measurement_equality.py` is code, not a concept, so it carries no frontmatter and this index names
it in prose. It checks two things about a run. Provenance: the computation that ran is the one the
concept sanctions. Fidelity: the value about to be displayed is the value the receipt carries.

Its `RECEIPT_FIELDS` tuple is the contract. Every name in a concept's `executor.receipt` must appear
there, and the gate checks it.
