# Test plan — graphrag

```
IDs      T-nn test case. S-nn scenario. J-nn user journey. All append-only.
Status   planned | in-progress | done | blocked | dropped
         blocked carries the observed behaviour. dropped carries one line of reason.
Columns  | ID | Title | S-nn | D-nn covered | Status | Test node ID |
```

The development plan is `development-plan.md` beside this file. It owns every `D-nn` named here.

# Scope

Under test: symbol extraction, the resolution ranking, the graph store and traversal. Also under
test: the four MCP tools, the CLI, the watcher and the operational surfaces. The fleet registration
and the two-engine gate live in the `ccw` repo, and a live session exercises them.

Named exclusions, each with its reason.

- The SCIP overlay ships no code this pass, so `T-18` and `T-19` stay `planned`.
- Grammar correctness belongs to `tree-sitter-language-pack`, and is not re-tested here.
- The parser download needs network. It is proven once by hand, and not in the suite.
- `coderag` itself is not under test. Only the boundary between the two engines is.

# Scenarios

Each scenario is one behavior, in the ISO/IEC/IEEE 29119-3 shape.

**S-01 Extraction is correct.**
Precondition: a fixture repo with a known symbol set.
Action: the extractor runs over it.
Expected: the symbol counts equal the recorded goldens for that language.

**S-02 Import scoping collapses the candidate set.**
Precondition: the CPython standard library at a pinned tag.
Action: references resolve by global name, and then by import scope.
Expected: the mean candidate file count falls by at least six times, measured 10.86 to 1.49.

**S-03 A gap is reported.**
Precondition: a language whose grammar emits no call capture.
Action: a caller question arrives for a symbol in that language.
Expected: the answer names the missing capability.

**S-04 Traversal terminates.**
Precondition: a fixture with a known import cycle.
Action: `blast_radius` runs from a node inside the cycle.
Expected: the answer is bounded, and no node is counted twice.

**S-05 Extraction stays fast.**
Precondition: a fixture corpus and one core.
Action: parsing and the tags query run over it.
Expected: throughput stays above the floor, and the floor names the measurement that set it.

**S-06 SCIP upgrades and never contradicts.**
Precondition: a typed project, indexed with the overlay and without it.
Action: the two runs are compared edge by edge.
Expected: resolved edges rise, and no resolved edge disagrees on its target file.

**S-07 The floor is durable.**
Precondition: a store stamped with an older extraction algorithm number.
Action: the indexer opens it.
Expected: it wipes and rebuilds, and it never alters the schema in place.

**S-08 The surfaces answer honestly.**
Precondition: a running daemon and a tool call with an unknown argument.
Action: the call is served.
Expected: the error names the valid set, and no corpus is widened.

**S-09 Operations degrade honestly.**
Precondition: a daemon that is down, or an identity that failed one check.
Action: the health rule runs.
Expected: it reports the state, and it pages on no single sample.

**S-10 A session reaches the engine.**
Precondition: a fresh session in a repo the engine holds.
Action: a structural question arrives.
Expected: the graph tool is called, and that call lifts the tree-walk denial.

**S-12 The index pass follows the content hash.**
Precondition: a repo indexed once.
Action: the pass runs again, unchanged and then after one edit.
Expected: the unchanged pass parses nothing, and the edited one parses the tree.

**S-11 The bundle carries its own guarantees.**
Precondition: a concept declaring an attested computation.
Action: the pre-push gate runs.
Expected: a missing attester or an unread receipt field fails the push.

# Cases

| ID | Title | S-nn | D-nn covered | Status | Test node ID |
|---|---|---|---|---|---|
| T-01 | An incompatible meta stamp forces a rebuild | S-07 | D-01 | done | tests/test_store.py::test_incompatible_meta_rebuilds |
| T-02 | Registry mutation loads inside the lock | S-07 | D-01 | done | tests/test_registry.py::test_mutate_loads_inside_the_lock |
| T-03 | Python golden symbol counts hold | S-01 | D-02 | done | tests/test_extract.py::test_python_golden_symbol_counts |
| T-04 | TypeScript needs the JavaScript query too | S-01 | D-02 | done | tests/test_queries.py::test_typescript_concatenates_javascript |
| T-05 | Every capture name is mapped or ignored | S-01 | D-02 | done | tests/test_queries.py::test_every_capture_name_is_known |
| T-06 | The capability counts hold under the pin | S-03 | D-02 | done | tests/test_grammars.py::test_capability_counts_under_the_pin |
| T-07 | Import scoping beats global matching | S-02 | D-03 | done | tests/test_resolve.py::test_import_scoping_collapses_candidates |
| T-08 | An unknown name becomes an external node | S-02 | D-03 | done | tests/test_resolve.py::test_unknown_name_is_external |
| T-09 | Blast radius terminates on a cycle | S-04 | D-04 | done | tests/test_index.py::test_blast_radius_terminates_over_the_cycle |
| T-10 | Parse and query stay above the floor | S-05 | D-04 | done | tests/test_perf.py::test_extraction_throughput_floor |
| T-11 | Every import query compiles and extracts | S-01 | D-05 | planned | tests/test_import_queries.py::test_each_language_extracts_an_import |
| T-12 | The four tool schemas are conformant | S-08 | D-06 | planned | tests/test_tools.py::test_tool_schemas_are_conformant |
| T-13 | Neighbors carries confidence and evidence | S-08 | D-06 | planned | tests/test_tools.py::test_neighbors_carries_confidence |
| T-14 | A missing capability is named, not empty | S-03 | D-06 | planned | tests/test_tools.py::test_missing_capability_is_reported |
| T-15 | An unknown argument names the valid set | S-08 | D-06 | planned | tests/test_tools.py::test_unknown_argument_names_valid_set |
| T-16 | One edit reparses one file | S-09 | D-07 | planned | tests/test_watch.py::test_single_edit_reparses_one_file |
| T-17 | Health pages on the second failure only | S-09 | D-07 | planned | tests/test_health.py::test_two_sample_rule |
| T-18 | Two indexers agree on a non-ASCII range | S-06 | D-08 | planned | tests/test_scip_offsets.py::test_non_ascii_ranges_agree |
| T-19 | A collapsed SCIP index is refused | S-06 | D-08 | planned | tests/test_scip_guard.py::test_collapsed_index_is_refused |
| T-20 | Five profiles carry the graphrag entry | S-10 | D-09 | planned | tests/test_fleet.py::test_five_profiles_carry_the_entry |
| T-21 | The port is fixed and a collision errors | S-10 | D-09 | planned | tests/test_server.py::test_port_collision_names_the_port |
| T-22 | Either engine lifts the walk denial | S-10 | D-10 | planned | tests/test_gate.py::test_either_engine_lifts_the_denial |
| T-23 | An empty graph answer buys no marker | S-10 | D-10 | planned | tests/test_gate.py::test_empty_answer_buys_no_marker |
| T-24 | A graph-only project is still gated | S-10 | D-10 | planned | tests/test_gate.py::test_graph_only_project_is_gated |
| T-25 | Plan mode still escapes the gate | S-10 | D-10 | planned | tests/test_gate.py::test_plan_mode_escapes |
| T-26 | The unit reports started after the store opens | S-09 | D-11 | planned | tests/test_systemd.py::test_notify_after_store_open |
| T-27 | The reach hook enrols the session root | S-10 | D-11 | planned | tests/test_systemd.py::test_reach_registers_the_root |
| T-28 | The bundle root declares its OKF version | S-11 | D-12 | done | tests/test_bundle.py::test_root_index_declares_okf_version |
| T-29 | The attester accepts a sound receipt | S-11 | D-13 | done | tests/test_attester.py::test_sound_receipt_is_accepted |
| T-30 | The attester rejects a changed number | S-11 | D-13 | done | tests/test_attester.py::test_changed_number_is_rejected |
| T-31 | An offset-free stale date is rejected | S-11 | D-14 | done | tests/test_bundle.py::test_offset_free_stale_after_is_rejected |
| T-32 | A dropped receipt field fails the check | S-11 | D-14 | done | tests/test_bundle.py::test_dropped_receipt_field_fails |
| T-33 | TypeScript and PHP golden counts hold | S-01 | D-02 | done | tests/test_extract.py::test_typescript_golden_symbol_counts |
| T-34 | A PHP static call needs the repair layer | S-01 | D-02 | done | tests/test_extract.py::test_a_php_static_call_needs_the_repair_layer |
| T-35 | One import row per import statement | S-01 | D-02 | done | tests/test_extract.py::test_one_import_row_per_statement |
| T-36 | A same-class call outranks every homonym | S-02 | D-03 | done | tests/test_resolve.py::test_a_same_class_call_beats_every_other_candidate |
| T-37 | A global set below the floor is dropped | S-02 | D-03 | done | tests/test_resolve.py::test_a_global_set_below_the_floor_is_dropped_rather_than_ranked |
| T-38 | Every concept carries the families this repo writes | S-11 | D-12 | done | tests/test_bundle.py::test_every_concept_carries_the_families_this_repo_writes |
| T-39 | A timestamp survives a round trip through this reader | S-11 | D-12 | done | tests/test_bundle.py::test_a_timestamp_survives_a_round_trip_through_this_reader |
| T-40 | No link in the bundle starts at the root | S-11 | D-12 | done | tests/test_bundle.py::test_no_link_in_the_bundle_starts_at_the_root |
| T-41 | A run against another corpus is rejected | S-11 | D-13 | done | tests/test_attester.py::test_a_run_against_another_corpus_is_rejected |
| T-42 | A missing receipt field is named | S-11 | D-13 | done | tests/test_attester.py::test_a_missing_receipt_field_is_named_rather_than_skipped |
| T-43 | A claim no receipt field carries is refused | S-11 | D-13 | done | tests/test_attester.py::test_a_claim_no_receipt_field_carries_is_refused |
| T-44 | An empty claim attests nothing | S-11 | D-13 | done | tests/test_attester.py::test_an_empty_claim_attests_nothing_and_a_partial_one_attests_itself |
| T-45 | A pass writes nodes and edges | S-12 | D-04 | done | tests/test_index.py::test_a_pass_writes_nodes_and_edges |
| T-46 | An unchanged tree is not reparsed | S-12 | D-04 | done | tests/test_index.py::test_an_unchanged_tree_is_not_reparsed |
| T-47 | A changed file makes the pass run | S-12 | D-04 | done | tests/test_index.py::test_a_changed_file_makes_the_pass_run |
| T-48 | The queue drops a queued job and requeues a running one | S-12 | D-04 | done | tests/test_index.py::test_the_queue_drops_a_queued_job_and_requeues_a_running_one |
| T-49 | Callers of a function in the cycle | S-04 | D-04 | done | tests/test_index.py::test_callers_of_a_function_in_the_cycle |
| T-50 | A depth over the ceiling is refused | S-04 | D-04 | done | tests/test_index.py::test_a_depth_over_the_ceiling_is_refused |
| T-51 | An unknown question names the valid set | S-03 | D-04 | done | tests/test_index.py::test_an_unknown_question_names_the_valid_set |
| T-52 | An unknown symbol is a gap and not an empty list | S-03 | D-04 | done | tests/test_index.py::test_an_unknown_symbol_is_a_gap_and_not_an_empty_list |
| T-53 | An unknown direction is refused | S-04 | D-04 | done | tests/test_index.py::test_an_unknown_direction_is_refused |
| T-54 | find_symbol returns a location and never a body | S-08 | D-04 | done | tests/test_index.py::test_find_symbol_returns_a_location_and_never_a_body |
| T-55 | The capability report names every language present | S-03 | D-04 | done | tests/test_index.py::test_the_capability_report_names_every_language_in_the_project |

# User journeys

The user of this product is an agent, so a journey is a tool-call sequence. Its acceptance is the
answer the agent can act on, never a green assertion.

**J-01 Enrol and index a fresh repo.** Call `index` on a repo the engine has never seen. Then read
`graphrag doctor`. Acceptance: the tier report names every language present in the tree.

**J-02 Find the callers of a known function.** Ask `neighbors` for callers. Acceptance: each caller
carries `confidence` and `evidence`, so the agent can tell a fact from a guess.

**J-03 Cross a known cycle.** Ask `blast_radius` over a fixture that cycles. Acceptance: the answer
terminates, lists each node once, and says where the depth ceiling cut it.

**J-04 Query a language with no grammar tags.** Ask for callers in C. Acceptance: the reply says C
has no call capture in this project. An empty list here is a journey failure.

**J-05 Enable the SCIP overlay.** Index a typed project with the tier on. Acceptance: resolved
edges rise, and no edge contradicts the tree-sitter target file.

**J-06 Re-index after one edit.** Change one file and wait for the watcher. Acceptance: the
progress file shows one file reparsed, and not the tree.

**J-07 Route two questions unprompted.** From a fresh session, ask a meaning question. Then ask a
caller question. Acceptance: each reaches the engine the routing rule names, with neither engine
named in the prompt.

**J-08 Measure the two engines against each other.** Run a caller-question set against both. Score
both against hand-verified edges. Acceptance: the numbers exist and are recorded. This journey is
the evidence that no record holds today, and its result graduates to `knowledge/computations/`.

# Experience bar

One rule, stated once and applied to every journey. **A gap is reported, never returned as an
absence.** Two empty results differ. One means the tool cannot answer that, and the other means
there are none. A caller acts on them differently, and only one of them is true.

Three qualities follow from it.

- Honest degradation. A daemon that is down says so, and never reports zero callers.
- An error names the valid set. An unknown language or edge kind is refused, never widened.
- No silent empty result. A case asserting an empty list, where the honest answer names a missing
  capability, is a passing test written over a defect.

`J-07` carries one more. The routing rule is selected, not merely written. A caller question that
reaches the semantic engine and stops there fails this plan, and not the prompt.

# Fixtures

Real, named, and built by `git init` in a temporary directory. No mocks, and no parser stubs.

- `tests/fixtures/wave1/` — one file per wave-one language, each holding a class, a method, a
  member call, a static call and four import shapes. One directory rather than one per language,
  because the goldens are read side by side and a split hides a difference between them.
- `tests/fixtures/c_small/` — C, which has no call capture. The gap fixture.
- The cycle fixture is three modules importing each other, built by the `repo` factory in
  `tests/test_index.py` rather than by a checked-in directory. It is five lines per module, and
  a directory on disk would hide them from the case that reads them.
- `tests/fixtures/unicode/` — a non-ASCII identifier, for the SCIP offset table.
- The CPython standard library at `v3.12.7`, cloned once into `~/.cache/graphrag/corpus`, for
  `T-07`. The case is marked `corpus` and skips when the clone is absent, so a fresh machine runs
  the suite without a network fetch. `GRAPHRAG_CORPUS_DIR` and `GRAPHRAG_CORPUS_REF` move it.

# Traceability

Every `T-nn` names exactly one `S-nn` and at least one `D-nn`. Every `D-nn` names at least one
`T-nn`. An ID is never reused and never deleted.

Two commands, run by the pre-push gate. Silence is the pass.

```sh
git ls-files > /tmp/tracked
awk -F'|' '/^\| D-[0-9]/ {print $5}' docs/development-plan.md | tr ',' '\n' | tr -d ' ' \
  | grep -vFx -f /tmp/tracked

uv run pytest --collect-only -q | sort > /tmp/collected
awk -F'|' '/^\| T-[0-9]/ {print $7}' docs/test-plan.md | tr -d ' ' | sort \
  | comm -23 - /tmp/collected
```

The pattern is `T-[0-9]`, never a bare `T-`, so the vocabulary block above is not read as a row.
The tree side is `git ls-files` rather than a walk, because the gate is about what a clone gets.
