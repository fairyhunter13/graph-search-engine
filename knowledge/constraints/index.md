# Constraint

* [A stale date without an explicit UTC offset reads as fresh
  forever](a-stale-date-needs-an-explicit-utc-offset.md) - OKF section 5 wants an absolute instant.
  An offset-free value parses, passes the standard rule set, and turns freshness checking off with
  no error, so the gate here runs the strict rule set.
* [Links here are relative, because the spec and the reference agent
  disagree](links-are-relative-because-the-bundle-is-browsed-on-github.md) - OKF section 6.1
  recommends a link that begins with a slash, and the upstream authoring prompt forbids one because
  it breaks GitHub rendering. Both are right about their own concern, and this bundle lives in a git
  repo.
