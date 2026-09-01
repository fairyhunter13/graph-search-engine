# Attesters

`measurement_equality.py` is code, not a concept, so it carries no frontmatter and this index names
it in prose. It checks two things about a run. Provenance: the computation that ran is the one the
concept sanctions. Fidelity: the value about to be displayed is the value the receipt carries.

Its `RECEIPT_FIELDS` tuple is the contract. Every name in a concept's `executor.receipt` must appear
there, and the gate checks it.

`two_engine_receipt.py` is the second contract. It declares the two-engine receipt shape and
delegates the comparison to `grade` in `measurement_equality.py`, because one module declares
exactly one `RECEIPT_FIELDS` and a union of two shapes would grade neither.

`freshness_receipt.py` is the third contract, and it declares the save-to-searchable shape: the two
latency arms, the file count, the sample count and the misses. It delegates to the same `grade`.
