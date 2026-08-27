# Reference

* [The fleet hook and the nightly sweep are recorded here, not
  linked](the-fleet-mechanisms-are-recorded-here-not-linked.md) - Two decisions rest on mechanisms
  that live in a private fleet repository. An unauthenticated fetch of that URL reads 404, so every
  concept citing it stays blocked in the nightly sweep. The facts are written down here instead.
* [The coderag CLI holds its own GPU session, and the card is
  shared](the-coderag-cli-holds-its-own-gpu-session.md) - The two-engine measurement drives
  `coderag search` twenty times, and every invocation builds its own CUDA session beside the
  daemon's. The card is 16303 MiB, the daemon holds 7660 MiB and one CLI search adds 3114 MiB, so a
  third consumer exhausts it.
