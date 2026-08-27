---
okf_version: "0.2"
---

# Subdirectories

* [attesters](attesters/index.md) - Deterministic code that grades a measurement receipt. No model
  call, no network, safe to run consumer-side.
* [constraints](constraints/index.md) - Facts about the ground this repo stands on, which no
  decision here can change.
* [decisions](decisions/index.md) - Choices taken, with the alternative rejected and the evidence
  that would reverse them.
* [computations](computations/index.md) - The load-bearing numbers, each one a contract naming its
  executor, its receipt and its attester.
* [policies](policies/index.md) - The rules this repo holds itself to, including the OKF profile
  it runs and why that profile is stricter than the spec.
* [skills](skills/index.md) - The run procedures an Attested Computation names in its executor.
* [defects](defects/index.md) - what went wrong here, what caused it, and what holds it now.
