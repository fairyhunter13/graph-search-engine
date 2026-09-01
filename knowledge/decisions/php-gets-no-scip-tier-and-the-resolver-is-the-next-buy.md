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
`vendor/composer/installed.php`. Measured across this estate: **0 of 69** `gen3-*` worktrees carry
`vendor/autoload.php`, and a Gen-1 PHP app, the Gen-2 PHP app and another PHP app carry no `composer.json`
at all.

Creating that is not one `composer install`. Each of 296 Gen-3 registry rows is a distinct pin with
its own dependency set, and the cost recurs on every new pin.

The upside is in the wrong place. The share of `external` calls whose callee name matches a
definition in the same project — a generous ceiling, because a name collision counts:

| Project | `external` CALLS | Ceiling | PHP callers only |
|---|---:|---:|---:|
| Gen-1 PHP app | 43,115 | 62.0% | 16,878 calls, **43.7%** |
| Gen-2 PHP app | 48,966 | 30.8% | 48,326 calls, 31.0% |
| Gen-3 `gen3-app-a` | 11,363 | 30.2% | 11,074 calls, 30.1% |
| Gen-3 `gen3-app-b` | 6,152 | 4.5% | 5,816 calls, 4.5% |

Read the last column, and never the third one, for a PHP ruling. A store holds every language in
the tree. The Gen-1 PHP app is two thirds JavaScript by call count, and its JavaScript ceiling is 73.7%, so
the store-wide 62.0% is mostly not a PHP number. The other three rows hold within one point either
way, measured 2026-08-30.

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

# What the Gen-1 miss is actually made of

The Gen-1 PHP app was re-measured on 2026-08-30, read-only against store
`gen1-php-app-1d64d72e801ee75b`. It holds 649 PHP files and 333 JavaScript files, and 61,613 `CALLS`
edges of which 43,115 read `external`. The rest are `same_file` 8,640, `global` 7,324,
`package` 1,608 and `same_class` 926. The four-way split of the 16,878 with a PHP caller, with
the builtin list taken from `get_defined_functions()` on PHP 8.3.6 rather than from a hand list:

| Slice of the 16,878 PHP `external` CALLS | Share |
|---|---:|
| Callee defined in the indexed project | **43.7%** |
| PHP builtin or language construct | 30.9% |
| Vendor, or first-party code in another store | 25.3% |

Every one of those 7,383 in-project calls is the second `external` write site in `resolve.py`, not
the first. The first site fires when `table.defines(name)` returns nothing, and a name defined in
the project makes that pool non-empty. So receiver narrowing at `resolve.py:145` emptied the pool,
and each of the 7,383 is a resolver miss by construction.

Attributing each one to the call shape its own file carries:

| Shape in the caller file | Share |
|---|---:|
| `$this-><loaded-name>-><callee>()` | **52.8%** |
| Property receiver that names no loaded class | 15.9% |
| No receiver shape found in the file | 15.3% |
| `Class::<callee>()` | 8.2% |
| `$var-><callee>()` | 7.8% |

This is an attribution and not an exact count. `call_site_byte` does not land on the callee token
in this store, so the join is by file and callee name, and a file carrying two shapes for one name
is charged to the first row that matches.

The prediction held. `$this->load->model('yard_model')` then `$this->yard_model->GetAll()` is the
leading shape, and 89 loaded names plus 250 project classes cover 71.9% of the 5,947
`$this-><prop>-><name>(` sites in the indexed corpus. `mongo_db`, `tpl`, `item_model` and `auth_model`
lead the receivers. The 20 heaviest callees in the 7,383 are `where` 518, `model` 368,
`GetAll` 307, `render` 303, `post` 298, `item` 249, `GetContract` 228, `format_date_mongo` 197,
`get` 181, `Save` 174, `view` 155, `mongo_date` 147, `update` 139, `GetById` 128, `set` 119,
`getStyle` 118, `insert` 117, `GetData` 110, `aggregate` 97 and `GetId` 96. The head of that
list is the CI3 model and query-builder vocabulary. Two rows are not, and they bound the buy.
`format_date_mongo` and `mongo_date` are CI3 helpers in `application/helpers/`, which a
receiver rule never reaches. `getStyle` is defined only in `js/cufon/cufon.js`, so those 118
are the name collision the ceiling was warned to be generous about.

So the Gen-1 buy is narrower than "fix the resolver". A CI3 receiver rule that reads
`$this->load->model()` and `$this->load->library()` into a property-to-class map reaches about half
of the largest in-project miss in the estate, and it needs no import work and no external tool.
That does not move the ruling above. It names which half of it to buy first.

# Re-opened on 2026-08-31, and the ruling holds

A token census of the caller's own workspace asked whether this deferral should move. Over 7 days
that workspace ran 54,496 Bash commands, 7,324 tree searches and 450 index searches. Over 2 days
only 1 of 39 searching sessions reached an index first. PHP is the estate's largest language, and
a PHP caller question has no precise answer here, so a session that asks one falls back to a tree
search.

That reading raises the cost of the gap. It does not touch any of the three blockers above. No
bridge exists, the byte-offset precondition is still untested, and CodeIgniter 3 still has no
extension. So PHPStan stays deferred, and the evidence argues for the resolver, which this
decision already names as the next buy.

One thing did change on the caller's side. The `php-lsp` plugin is now enabled, and `intelephense`
is installed. A language server answers a definition and a reference inside one open project, at
edit time. It writes no edge into the graph, so it narrows the daily cost of the gap and it closes
none of it.

# Re-confirmed 2026-09-01, over five times the population

A later plan proposed reversing this: fill `scip-php`'s command and measure one PHP repository
whose `vendor/` is already present. The precondition was re-measured over the whole estate rather
than argued, because this record's own figure was taken on 69 worktrees.

`scip-php` hard-requires four files at the build root: `composer.json`, `composer.lock`,
`vendor/autoload.php` returning a real `ClassLoader`, and `vendor/composer/installed.php`. Across
**333 PHP roots**, exactly **one** carries all four. It is a 468-file application holding 2,042
calls. A further 103 are partial.

A first probe read 11 candidates by globbing `vendor/autoload.php` at any depth. That counted
bundled plugin vendors under trees carrying no root `composer.json` -- a different population than
the precondition names, and the reason a census must state what it read. The corrected figure is
one.

So the plan's exit condition is technically meetable exactly once, on a corpus that decides nothing
for an estate, while the recoverable-miss generation this record identifies is the one `scip-php`
cannot read at all. The empty command stays. `T-265` asserts that `readiness` reports it as
`manual` and never `absent`, which is what keeps the emptiness legible as a ruling rather than as
a missing download.

Related: [which languages get a SCIP tier](which-languages-get-a-scip-tier.md), which places this
refusal beside the other eight,
[scip is an overlay and never the extractor](scip-is-an-overlay-and-never-the-extractor.md),
[a submodule is invisible to discovery](../defects/a-submodule-is-invisible-to-discovery.md).
