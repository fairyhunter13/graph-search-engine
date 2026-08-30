---
type: Decision
resource: src/graphrag/scip/run.py
title: PHP gets no SCIP tier, PHPStan is deferred, and the resolver is the next buy
description: "`scip-php` is registered with no command, and it stays that way. It needs a Composer install no PHP tree in this estate has, and the generations where the miss is recoverable are CodeIgniter, which it cannot read. PHPStan is the stronger instrument and needs a bridge nobody has written. The measured ceiling says fix the resolver instead."
tags: [scip, php, phpstan, resolution, measurement, gen-1, gen-2, gen-3]
status: stable
generated: { by: claude/opus-5, at: 2026-08-30T00:00:00Z }
---

# The ruling

`Indexer("scip-php", ("php",), False, True)` in `scip/run.py` keeps an empty `command`, so it is
registered and not invocable. That is deliberate. A reader who finds it should not read it as an
unfinished job.

PHPStan is deferred rather than refused. It is the better instrument, and buying it needs a
collector and a SCIP emitter that do not exist.

Neither is the next buy. The resolver is.

# Why scip-php is refused

It derives its whole file set from Composer. `src/Composer/Composer.php` hard-requires
`composer.json`, `composer.lock`, a `vendor/autoload.php` returning a real `ClassLoader`, and
`vendor/composer/installed.php`. Measured across this estate: **0 of 69** `gen3-app-*` worktrees carry
`vendor/autoload.php`, and `gen1-php-app`, `gen2-php-app` and `domain-service` carry no `composer.json`
at all.

Creating that is not one `composer install`. Each of 296 Gen-3 registry rows is a distinct pin with
its own dependency set, and the cost recurs on every new pin.

The upside is in the wrong place. The share of `external` calls whose callee name matches a
definition in the same project — a generous ceiling, because a name collision counts:

| Project | `external` CALLS | Ceiling |
|---|---:|---:|
| Gen-1 `gen1-php-app` | 43,115 | **62.0%** |
| Gen-2 `gen2-php-app` | 48,966 | **30.8%** |
| Gen-3 `gen3-app-a` | 11,363 | 30.2% |
| Gen-3 `gen3-app-b` | 6,152 | 4.5% |

The two generations holding the recoverable miss are CodeIgniter 3. They have no autoload map, and
the CI3 idiom `$this->load->model('Foo_model')` then `$this->Foo_model->bar()` runs through
`CI_Controller::__get`, which scip-php does not implement. It has no local-variable type inference
either: `Types::type()` returns a type for a `Variable` only when it is `$this`.

The tool is also a single-maintainer dependency whose published artifacts are broken. The latest
release is v0.0.2 of 2023-04-23, and open issue #862 reports the README install path crashing. Only
a clone of `main` works.

# Why PHPStan is deferred rather than refused

It beats scip-php on both counts that refused scip-php. Static reflection reads first-party code
from source, so a missing `vendor/` **degrades** the answer instead of stopping the run. `Scope::getType()`
gives real inference. Larastan covers Laravel facades, Eloquent and container bindings.
`scanDirectories:` reaches a submodule, and `gen3-app-d/v1.3.14/phpstan.neon` already uses
`scanDirectories: Domain`.

Three things stop it being bought now.

1. **No bridge exists.** `phpdepend/callmap` omits byte offsets. `shipmonk/dead-code-detector` and
   `tomasvotruba/unused-public` keep their graph internal. A `MethodCall` collector plus a SCIP
   emitter is work this estate would own. The engine side is ready: `producer` in `store.py` is
   free text, and `tests/scipwrite.py` is a stdlib SCIP writer graded against `protoc --decode`.
2. **One precondition is unverified.** Ingest joins on an exact `(file_id, start_byte, end_byte)`
   triple. PHP-Parser 5 sets `getStartFilePos()` unconditionally and PHPStan 2.x requires it, but
   whether the cached-parser path preserves the offsets is untested. PHPStan's error channel
   carries a line number only, so they must ride inside the collector payload. Test this first.
3. **CodeIgniter 3 has no extension**, and CI3 is where the 62% and 30.8% ceilings live.
   `CodeIgniter/phpstan-codeigniter` is CI4-only.

The estate's existing PHPStan is not a head start. 117 roots carry a config across four PHPStan
majors, 5 pinned to `"*"`, only 23 enforced in CI and 0 of 75 Jenkinsfiles invoking one.

# Why the resolver is the next buy

The corpus caps every resolver. Decomposing the `gen3-app-a` miss by where each callee is
actually defined, after the submodule fix:

| Slice of the 11,363 `external` CALLS | Share |
|---|---:|
| Callee defined in the indexed project | **30.2%** |
| PHP builtin or language construct | 18.7% |
| Vendor, or first-party code in another store | 51.2% |

`ingest._rewrite_call` joins a callee to a node in the same store, so the bottom two rows are
unwritable whatever resolves them. `is_null`, `response`, `app` and `assertArrayHasKey` lead that
list, and no policy change should pull PHPUnit and Laravel into the graph.

The top row is the whole prize, it is entirely in-project, and it needs no external tool. 2,645 of
those calls name a symbol defined under `Domain/` in the same store and still read `external`. That
is [module identity is Python-shaped](../defects/module-identity-is-python-shaped.md), and closing it
is cheaper than either indexer.

Related: [scip is an overlay and never the extractor](scip-is-an-overlay-and-never-the-extractor.md),
[a submodule is invisible to discovery](../defects/a-submodule-is-invisible-to-discovery.md).
