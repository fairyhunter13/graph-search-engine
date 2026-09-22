# Policy

* [This bundle is a strict profile of OKF v0.2, and a producer may be stricter than a
  consumer](this-bundle-is-a-strict-profile-of-okf.md) - OKF v0.2 names no fixed taxonomy and
  forbids a consumer from rejecting a bundle over an unknown type. The gate here refuses one. The
  two are not in conflict, because the rule the spec writes is a rule for readers, and this repo
  is a writer.
* [Evidence from a private corpus travels as a measurement, never as an
  identifier](private-evidence-is-a-measurement-not-an-identifier.md) - this repository is public
  and most of its defects are found on private code. A count carries the finding and names
  nothing. The ban list cannot enforce this: it holds the names somebody thought to add, and a
  type name borrowed from a client's tree is never one of them.
