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

- The SCIP overlay needs a resolved build per language, so `T-18` and `T-19` grade the reader
  and the coverage guard against a golden index, and never a live indexer run.
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
Expected: the mean candidate file count falls by at least six times, measured 10.86 to 1.19.

**S-03 A gap is reported.**
Precondition: a language whose grammar emits no call capture.
Action: a caller question arrives for a symbol in that language.
Expected: the answer names the missing capability.

**S-13 A vendored query compiles against its own grammar.**
Precondition: an import query naming a node type the grammar does not carry.
Action: the extractor runs the query over a file in that language.
Expected: the compile case fails and names the language, rather than the file reporting no imports.

**S-04 Traversal terminates.**
Precondition: a fixture with a known import cycle.
Action: `blast_radius` runs from a node inside the cycle.
Expected: the answer is bounded, and no node is counted twice.

**S-05 Extraction stays fast.**
Precondition: a fixture corpus and one core.
Action: parsing and the tags query run over it.
Expected: throughput stays above the floor, and the floor names the measurement that set it.

**S-06 SCIP upgrades and never contradicts.**
Precondition: a project tree-sitter has already indexed, and one SCIP index over it.
Action: the overlay reads that index against the tree-sitter census.
Expected: a definition is upgraded and never replaced, a call edge is rewritten only where
tree-sitter recorded a call at the same byte, and an index that covers too little is refused
before any write.

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

**S-14 The routing rule is graded.**
Precondition: a caller-question set, and a ground truth read by hand over the whole tracked tree.
Action: the graph engine and both semantic modes answer each question.
Expected: the graph scores highest overall, and it is exact only where the name is distinctive.

**S-15 The module shape holds.**
Precondition: the tracked source tree.
Action: the hygiene suite reads every module.
Expected: no module passes the line ceiling, carries a home path or imports a sibling from
`config.py`, `scip` is the only subpackage, and the name ban fails closed where it is unset.

**S-16 A push that skipped the hook still meets a gate.**
Precondition: the workflow file, and a run on `main`.
Action: the suite, the linter and the bundle checks run.
Expected: every action is pinned to a commit, no step continues on error, and the token reads only.

**S-17 A procedure is selected, not named.**
Precondition: two scratch packages outside the fleet repos, one earning a plan pair and one not.
Action: a headless session is asked for a test plan, with no skill named.
Expected: the earning repo dispatches the skill, and the one-file service does not.

**S-18 The plan pair is graded by something that runs.**
Precondition: the two plan documents, and the tracked tree they anchor into.
Action: the suite runs.
Expected: every `done` row resolves to a test that exists, every owned path to a file that is
tracked, and every test to a row that names it.

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
| T-06 | 68 tagged grammars: 67 defs, 50 calls by pack and 52 effective, 17 impls | S-03 | D-02 | done | tests/test_grammars.py::test_capability_counts_under_the_pin |
| T-07 | Import scoping beats global matching | S-02 | D-03 | done | tests/test_resolve.py::test_import_scoping_collapses_candidates |
| T-08 | An unknown name becomes an external node | S-02 | D-03 | done | tests/test_resolve.py::test_unknown_name_is_external |
| T-09 | Blast radius terminates on a cycle | S-04 | D-04 | done | tests/test_index.py::test_blast_radius_terminates_over_the_cycle |
| T-10 | Parse and query stay above the floor | S-05 | D-04 | done | tests/test_perf.py::test_extraction_throughput_floor |
| T-11 | Every import query compiles and extracts | S-01 | D-05 | done | tests/test_import_queries.py::test_each_language_extracts_an_import |
| T-12 | The four tool schemas are conformant | S-08 | D-06 | done | tests/test_tools.py::test_tool_schemas_are_conformant |
| T-13 | Neighbors carries confidence and evidence | S-08 | D-06 | done | tests/test_tools.py::test_neighbors_carries_confidence |
| T-14 | A missing capability is named, not empty | S-03 | D-06 | done | tests/test_tools.py::test_missing_capability_is_reported |
| T-15 | An unknown argument names the valid set | S-08 | D-06 | done | tests/test_tools.py::test_unknown_argument_names_valid_set |
| T-16 | One edit raises one index pass | S-09 | D-07 | done | tests/test_watch.py::test_single_edit_reparses_one_file |
| T-17 | Health pages on the second failure only | S-09 | D-07 | done | tests/test_health.py::test_two_sample_rule |
| T-18 | Two indexers agree on a non-ASCII range | S-06 | D-08 | done | tests/test_scip_offsets.py::test_non_ascii_ranges_agree |
| T-19 | A collapsed SCIP index is refused | S-06 | D-08 | done | tests/test_scip_guard.py::test_collapsed_index_is_refused |
| T-20 | Five profiles carry the graphrag entry | S-10 | D-09 | done | (ccw) internal/hooks/mcpsync_test.go::TestFiveProfilesCarryBothEngines |
| T-21 | The port is fixed and a collision errors | S-10 | D-06, D-09 | done | tests/test_server.py::test_port_collision_names_the_port |
| T-22 | Either engine lifts the walk denial | S-10 | D-10 | done | (ccw) internal/hooks/twoengines_internal_test.go::TestEitherEngineLiftsTheWalkDenial |
| T-23 | An empty graph answer buys no marker | S-10 | D-10 | done | (ccw) internal/hooks/twoengines_internal_test.go::TestAnEmptyGraphAnswerBuysNoMarker |
| T-24 | A graph-only project is still gated | S-10 | D-10 | done | (ccw) internal/hooks/twoengines_internal_test.go::TestAGraphOnlyProjectIsStillGated |
| T-25 | Plan mode still escapes the gate | S-10 | D-10 | done | (ccw) internal/hooks/twoengines_internal_test.go::TestPlanModeEscapesForEitherEngine |
| T-26 | The unit reports started after the store opens | S-09 | D-11 | done | tests/test_systemd.py::test_notify_after_store_open |
| T-27 | The reach hook enrols the session root | S-10 | D-11 | done | tests/test_systemd.py::test_reach_registers_the_root |
| T-28 | The bundle root declares its OKF version | S-11 | D-12 | done | tests/test_bundle.py::test_root_index_declares_okf_version |
| T-29 | The attester accepts a sound receipt | S-11 | D-13 | done | tests/test_attester.py::test_sound_receipt_is_accepted |
| T-30 | The attester rejects a changed number | S-11 | D-13 | done | tests/test_attester.py::test_changed_number_is_rejected |
| T-31 | An offset-free stale date is rejected | S-11 | D-14 | done | tests/test_bundle.py::test_offset_free_stale_after_is_rejected |
| T-32 | A dropped receipt field fails the check -- dropped: the attester-contract gate went with `scripts/check_attester_contract.py` in `832b1bb` | S-11 | D-14 | dropped | tests/test_bundle.py::test_dropped_receipt_field_fails |
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
| T-48 | The queue drops a queued job and requeues a running one -- dropped: superseded by `T-284`, which names the same test after `D-48` renamed the verdict `dropped` to `merged` | S-12 | D-04 | dropped | tests/test_index.py::test_the_queue_drops_a_queued_job_and_requeues_a_running_one |
| T-49 | Callers of a function in the cycle | S-04 | D-04 | done | tests/test_index.py::test_callers_of_a_function_in_the_cycle |
| T-50 | A depth over the ceiling is refused | S-04 | D-04 | done | tests/test_index.py::test_a_depth_over_the_ceiling_is_refused |
| T-51 | An unknown question names the valid set | S-03 | D-04 | done | tests/test_index.py::test_an_unknown_question_names_the_valid_set |
| T-52 | An unknown symbol is a gap and not an empty list | S-03 | D-04 | done | tests/test_index.py::test_an_unknown_symbol_is_a_gap_and_not_an_empty_list |
| T-53 | An unknown direction is refused | S-04 | D-04 | done | tests/test_index.py::test_an_unknown_direction_is_refused |
| T-54 | find_symbol returns a location and never a body | S-08 | D-04 | done | tests/test_index.py::test_find_symbol_returns_a_location_and_never_a_body |
| T-55 | The capability report names every language present | S-03 | D-04 | done | tests/test_index.py::test_the_capability_report_names_every_language_in_the_project |
| T-56 | Every vendored import query compiles | S-13 | D-05 | done | tests/test_import_queries.py::test_every_vendored_import_query_compiles |
| T-57 | Every vendored query has a sample | S-13 | D-05 | done | tests/test_import_queries.py::test_every_vendored_query_has_a_sample |
| T-58 | A language with no import query says so | S-03 | D-05 | done | tests/test_import_queries.py::test_a_language_with_no_import_query_says_so |
| T-59 | A source root prefix leaves the module name | S-02 | D-15 | done | tests/test_resolve.py::test_a_source_root_prefix_leaves_the_module_name |
| T-60 | The capability table reads the manifest, not the cache | S-03 | D-02 | done | tests/test_grammars.py::test_known_languages_does_not_depend_on_the_download_cache |
| T-61 | The bridge round trips one call | S-08 | D-06 | done | tests/test_server.py::test_the_bridge_round_trips_one_call |
| T-62 | A dead daemon keeps stdout clean | S-08 | D-06 | done | tests/test_server.py::test_the_bridge_survives_an_unreachable_daemon |
| T-63 | An unindexed root names the index tool | S-08 | D-06 | done | tests/test_tools.py::test_an_unindexed_root_names_the_index_tool |
| T-64 | Doctor prints the capability table | S-03 | D-06 | done | tests/test_tools.py::test_doctor_prints_the_capability_table |
| T-65 | Federation expands one level, not transitively | S-10 | D-16 | done | tests/test_federation.py::test_federation_expands_one_level |
| T-66 | Progress carries a rate and an eta | S-09 | D-07 | done | tests/test_watch.py::test_progress_reports_a_pass_and_then_an_idle |
| T-67 | The progress file is keyed the way the graph is | S-09 | D-07 | done | tests/test_watch.py::test_an_index_pass_writes_its_progress_file |
| T-68 | A rotated ledger still answers | S-09 | D-07 | done | tests/test_watch.py::test_the_ledger_rotates_and_still_answers |
| T-69 | A failed pass leaves a row and a registry error | S-09 | D-07 | done | tests/test_watch.py::test_a_failed_pass_leaves_a_row_and_a_registry_error |
| T-70 | A refused file never wakes the indexer | S-09 | D-07 | done | tests/test_watch.py::test_a_file_the_indexer_would_refuse_never_wakes_it |
| T-71 | An unchanged reconcile does not re-arm | S-09 | D-07 | done | tests/test_watch.py::test_rearm_only_when_the_watched_set_moved |
| T-72 | A trace id reaches the error text | S-09 | D-07 | done | tests/test_watch.py::test_a_trace_id_reaches_the_error_text |
| T-73 | A healed project stops paging | S-09 | D-07 | done | tests/test_health.py::test_a_healed_project_stops_paging |
| T-74 | A dead worker pages with no project failing | S-09 | D-07 | done | tests/test_health.py::test_a_dead_worker_pages_though_no_project_is_failing |
| T-75 | A stalled queue pages at the stall | S-09 | D-07 | done | tests/test_health.py::test_a_stalled_queue_pages_at_the_stall |
| T-76 | An unreachable daemon is reported, not ranked | S-09 | D-07 | done | tests/test_health.py::test_an_unreachable_daemon_is_reported_not_ranked |
| T-77 | A member is an indirect claim | S-10 | D-16 | done | tests/test_federation.py::test_a_member_is_an_indirect_claim |
| T-78 | A member dropped from the config loses the claim | S-10 | D-16 | done | tests/test_federation.py::test_a_member_dropped_from_the_config_loses_the_claim |
| T-79 | An absent member is dropped rather than raised | S-10 | D-16 | done | tests/test_federation.py::test_an_absent_member_is_dropped_rather_than_raised |
| T-80 | A root federating itself is ignored | S-10 | D-16 | done | tests/test_federation.py::test_a_member_naming_itself_is_ignored |
| T-81 | A config that cannot be obeyed federates nothing | S-10 | D-16 | done | tests/test_federation.py::test_a_config_that_cannot_be_obeyed_federates_nothing |
| T-82 | Scope reaches a member and stops there | S-10 | D-16 | done | tests/test_federation.py::test_scope_reaches_a_member_and_stops_there |
| T-83 | The deepest enrolled root owns a path | S-10 | D-16 | done | tests/test_federation.py::test_the_deepest_enrolled_root_owns_a_path |
| T-84 | A peer is looked up, never guessed | S-10 | D-16 | done | tests/test_federation.py::test_this_process_is_named_by_its_own_source_port |
| T-85 | Only the three named units are enabled | S-09 | D-11 | done | tests/test_systemd.py::test_only_the_three_named_units_are_enabled |
| T-86 | Uninstall removes only what it wrote | S-09 | D-11 | done | tests/test_systemd.py::test_the_units_are_removed_by_name |
| T-87 | The notice names the languages that answer nothing | S-10 | D-11 | done | tests/test_systemd.py::test_the_notice_names_the_languages_that_answer_nothing |
| T-88 | An enrolled but unindexed root says so | S-10 | D-11 | done | tests/test_systemd.py::test_an_enrolled_but_unindexed_root_says_so |
| T-89 | An unreachable daemon refuses rather than reports nothing | S-10 | D-11 | done | tests/test_systemd.py::test_an_unreachable_daemon_refuses_rather_than_reports_nothing |
| T-90 | The registry row carries the reach figures | S-10 | D-17 | done | tests/test_index.py::test_the_registry_row_carries_the_figures_the_reach_hook_reads |
| T-91 | The graph wins the caller question, and only where the name is distinctive | S-14 | D-18 | done | tests/test_two_engine.py::test_the_graph_wins_the_caller_question |
| T-92 | The two-engine receipt is attested, and a moved number is refused | S-11 | D-18 | done | tests/test_two_engine.py::test_the_two_engine_receipt_is_attested |
| T-93 | A member call resolves to the module its receiver names | S-14 | D-19 | done | tests/test_resolve.py::test_the_receiver_picks_the_module |
| T-94 | Enumeration follows git and the shared indexable predicate | S-12 | D-01 | done | tests/test_discover.py::test_git_ignored_files_are_never_enumerated |
| T-95 | The diff reads content and never mtime | S-12 | D-01 | done | tests/test_discover.py::test_the_diff_ignores_mtime_and_reads_content |
| T-96 | A home or system directory is refused as a root | S-07 | D-01 | done | tests/test_discover.py::test_a_home_or_system_directory_is_refused_as_a_root |
| T-97 | The language count is what doctor reports | S-08 | D-01 | done | tests/test_discover.py::test_the_language_count_is_what_doctor_reports |
| T-98 | Strict config refuses an unknown key, a wrong type and a retired filename | S-07 | D-01 | done | tests/test_projcfg.py::test_an_unknown_key_is_an_error_that_names_the_closest_one |
| T-99 | Absent config is the defaults, and a valid one round trips | S-07 | D-01 | done | tests/test_projcfg.py::test_no_config_is_the_defaults |
| T-100 | The name ban fails closed where it is unset | S-15 | D-01 | done | tests/test_hygiene.py::test_the_name_ban_fails_closed_when_it_is_unset |
| T-101 | No module passes the line ceiling | S-15 | D-01 | done | tests/test_hygiene.py::test_every_module_is_under_the_line_ceiling |
| T-102 | The wire decoder agrees with `protoc --decode` | S-06 | D-08 | done | tests/test_scip_wire.py::test_the_decoder_agrees_with_protoc |
| T-103 | All three occurrence range shapes yield one span | S-06 | D-08 | done | tests/test_scip_read.py::test_all_three_range_shapes_yield_one_span |
| T-104 | A definition is upgraded and its unset kind is kept | S-06 | D-08 | done | tests/test_scip_ingest.py::test_a_definition_is_upgraded_and_its_kind_is_kept |
| T-105 | A call is rewritten only where tree-sitter found one | S-06 | D-08 | done | tests/test_scip_ingest.py::test_a_call_is_rewritten_only_where_tree_sitter_found_one |
| T-106 | An implementation relationship becomes an edge | S-06 | D-08 | done | tests/test_scip_ingest.py::test_an_implementation_relationship_becomes_an_edge |
| T-107 | A refusal is an outcome and never an exception | S-06 | D-08 | done | tests/test_scip_run.py::test_a_refusal_is_an_outcome_and_never_an_exception |
| T-108 | The index pass runs the overlay only where the config asks | S-06 | D-08 | done | tests/test_scip_run.py::test_the_index_pass_runs_the_overlay_only_where_the_config_asks |
| T-109 | An unknown indexer name is an error and never a guessed encoding | S-06 | D-08 | done | tests/test_scip_offsets.py::test_an_unknown_tool_is_an_error_and_never_a_guess |
| T-110 | A symbol descriptor tail carries the kind of each step | S-06 | D-08 | done | tests/test_scip_symbol.py::test_the_descriptor_tail_carries_the_kind_of_each_step |
| T-111 | The receipt on disk agrees with the concept | S-02 | D-21 | done | tests/test_resolve.py::test_the_receipt_on_disk_agrees_with_the_concept |
| T-112 | The workflow pins every action to a commit | S-16 | D-20 | done | tests/test_ci.py::test_the_workflow_pins_every_action |
| T-113 | The workflow token reads and never writes | S-16 | D-20 | done | tests/test_ci.py::test_the_workflow_reads_and_never_writes |
| T-114 | No step continues on error | S-16 | D-20 | done | tests/test_ci.py::test_no_step_continues_on_error |
| T-115 | It runs on main and by hand only | S-16 | D-20 | done | tests/test_ci.py::test_it_runs_on_main_and_by_hand_only |
| T-116 | A re-exported name resolves through the package initialiser | S-02 | D-22 | planned |  |
| T-117 | The live graph card reports the counts on disk | S-10 | D-11 | done | (ccw) internal/hooks/graphragreach_internal_test.go::TestALiveGraphReportsItsCounts |
| T-118 | A stopped graph daemon never reports an available graph | S-10 | D-11 | done | (ccw) internal/hooks/graphragreach_internal_test.go::TestAStoppedDaemonNeverReportsAnAvailableGraph |
| T-119 | An unenrolled directory with no daemon is unreachable, not absent | S-10 | D-11 | done | (ccw) internal/hooks/graphragreach_internal_test.go::TestAnUnenrolledDirectoryWithNoDaemonIsUnreachableNotAbsent |
| T-120 | A stopped coderag daemon reports itself down | S-10 | D-11 | done | (ccw) internal/hooks/coderagreach_internal_test.go::TestAStoppedCoderagDaemonReportsItselfDown |
| T-121 | The tier raises the resolved share and agrees with the parse | S-06 | D-08 | done | tests/test_scip_ingest.py::test_the_tier_raises_the_resolved_share_and_agrees_with_the_parse |
| T-122 | The two closed kind sets have a reader | S-01 | D-01 | done | tests/test_store.py::test_the_two_closed_sets_have_a_reader |
| T-123 | The two-engine receipt agrees with the concept | S-11 | D-21 | done | tests/test_two_engine.py::test_the_two_engine_receipt_agrees_with_the_concept |
| T-124 | Every evidence value a real index writes is declared | S-01 | D-23 | done | tests/test_tools.py::test_every_evidence_value_a_real_index_writes_is_declared |
| T-125 | A second ingest replaces its own implements edges | S-06 | D-24 | done | tests/test_scip_ingest.py::test_a_second_ingest_replaces_its_own_implements_edges |
| T-126 | Every relative link in the bundle resolves | S-11 | D-12 | done | tests/test_bundle.py::test_every_relative_link_in_the_bundle_resolves |
| T-127 | The two questions reach the engines in order | S-10 | D-26 | done | tests/test_probe.py::test_the_two_questions_reach_the_engines_in_order |
| T-128 | The plan skill is selected where it is earned | S-17 | D-26 | done | tests/test_probe.py::test_the_plan_skill_is_selected_where_it_is_earned |
| T-129 | A file over the byte ceiling is not indexable | S-12 | D-01 | done | tests/test_discover.py::test_a_file_over_the_ceiling_is_not_indexable |
| T-130 | A file with no grammar is never enumerated as source | S-12 | D-01 | done | tests/test_discover.py::test_a_file_with_no_grammar_is_not_enumerated_as_source |
| T-131 | A tree that is not a repo is walked | S-12 | D-01 | done | tests/test_discover.py::test_a_tree_that_is_not_a_repo_is_walked |
| T-132 | A call is scoped to the definition that encloses it | S-01 | D-02 | done | tests/test_extract.py::test_a_call_scope_is_the_enclosing_definition |
| T-133 | A method is recovered from containment | S-01 | D-02 | done | tests/test_extract.py::test_a_method_is_recovered_from_containment |
| T-134 | An unknown language is reported and never raised | S-03 | D-02 | done | tests/test_extract.py::test_an_unknown_language_is_reported_and_not_raised |
| T-135 | Every definition carries a line range | S-01 | D-02 | done | tests/test_extract.py::test_every_definition_carries_a_line_range |
| T-136 | PHP golden symbol counts hold | S-01 | D-02 | done | tests/test_extract.py::test_php_golden_symbol_counts |
| T-137 | A language with no grammar has no capability | S-03 | D-02 | done | tests/test_grammars.py::test_a_language_with_no_grammar_has_no_capability |
| T-138 | A missing capability is a sentence, and a present one is empty | S-03 | D-02 | done | tests/test_grammars.py::test_a_missing_capability_is_a_sentence_and_a_present_one_is_empty |
| T-139 | The capability table answers for every language asked of it | S-03 | D-02 | done | tests/test_grammars.py::test_the_capability_table_covers_what_it_is_asked_for |
| T-140 | TypeScript gains calls and C never does | S-03 | D-02 | done | tests/test_grammars.py::test_typescript_gains_calls_and_c_never_does |
| T-141 | A banned name in a module is caught | S-15 | D-01 | done | tests/test_hygiene.py::test_a_banned_name_in_a_module_is_caught |
| T-142 | The config module imports no sibling | S-15 | D-01 | done | tests/test_hygiene.py::test_config_imports_no_sibling |
| T-143 | No module carries a home path | S-15 | D-01 | done | tests/test_hygiene.py::test_no_module_carries_a_home_path |
| T-144 | The scip package is the only subpackage | S-15 | D-01 | done | tests/test_hygiene.py::test_scip_is_the_only_subpackage |
| T-145 | An empty config document is not an error | S-07 | D-01 | done | tests/test_projcfg.py::test_an_empty_document_is_not_an_error |
| T-146 | A valid config round trips every field | S-07 | D-01 | done | tests/test_projcfg.py::test_a_valid_config_round_trips_every_field |
| T-147 | A wrong type is rejected before it reaches the indexer | S-07 | D-01 | done | tests/test_projcfg.py::test_a_wrong_type_is_rejected_before_it_reaches_the_indexer |
| T-148 | The retired config filename is refused, not ignored | S-07 | D-01 | done | tests/test_projcfg.py::test_the_retired_filename_is_refused_and_not_ignored |
| T-149 | A capture name in a comment is not a capture | S-01 | D-02 | done | tests/test_queries.py::test_a_capture_name_in_a_comment_is_not_a_capture |
| T-150 | An import query follows the base language | S-13 | D-02 | done | tests/test_queries.py::test_an_import_query_follows_the_base_language |
| T-151 | An unmapped capture name is reported rather than dropped | S-01 | D-02 | done | tests/test_queries.py::test_an_unmapped_name_is_reported_rather_than_dropped |
| T-152 | The repair layer is appended and the pack query is untouched | S-01 | D-02 | done | tests/test_queries.py::test_the_repair_layer_is_appended_and_the_pack_query_is_untouched |
| T-153 | A symlinked path claims the row it points at | S-07 | D-01 | done | tests/test_registry.py::test_a_symlinked_path_claims_the_row_it_points_at |
| T-154 | Forget releases a member no surviving root claims | S-07 | D-01 | done | tests/test_registry.py::test_forget_releases_a_member_no_surviving_root_claims |
| T-155 | Forget writes one backup holding every row it removed | S-07 | D-01 | done | tests/test_registry.py::test_forget_writes_one_backup_holding_every_row_it_removed |
| T-156 | A missing path never prunes its registry row | S-07 | D-01 | done | tests/test_registry.py::test_nothing_prunes_a_row_because_its_path_is_missing |
| T-157 | The digest moves when a root is dropped, and the count does not | S-07 | D-01 | done | tests/test_registry.py::test_the_digest_moves_when_a_root_is_dropped_and_the_count_does_not |
| T-158 | An imported symbol beats a repo-wide homonym | S-02 | D-03 | done | tests/test_resolve.py::test_an_imported_symbol_beats_a_repo_wide_homonym |
| T-159 | An out-of-scope name falls to a ranked global set | S-02 | D-03 | done | tests/test_resolve.py::test_an_out_of_scope_name_falls_to_a_ranked_global_set |
| T-160 | A package initialiser names the package | S-02 | D-15 | done | tests/test_resolve.py::test_a_package_initialiser_names_the_package |
| T-161 | A relative import resolves against the importing directory | S-02 | D-15 | done | tests/test_resolve.py::test_a_relative_import_resolves_against_the_importing_directory |
| T-162 | A self receiver still reaches the enclosing class | S-02 | D-19 | done | tests/test_resolve.py::test_a_self_receiver_still_reaches_the_enclosing_class |
| T-163 | The definition unit counts higher than the file unit | S-02 | D-03 | done | tests/test_resolve.py::test_the_definition_unit_is_higher_than_the_file_unit |
| T-164 | A full index with no definitions is refused too | S-06 | D-08 | done | tests/test_scip_guard.py::test_a_full_index_with_no_definitions_is_refused_too |
| T-165 | A language this project does not hold is refused by name | S-06 | D-08 | done | tests/test_scip_guard.py::test_a_language_this_project_does_not_hold_is_refused_by_name |
| T-166 | The coverage guard reads and never writes | S-06 | D-08 | done | tests/test_scip_guard.py::test_the_guard_reads_and_never_writes |
| T-167 | A definition at a byte no node holds is dropped | S-06 | D-08 | done | tests/test_scip_ingest.py::test_a_definition_at_a_byte_no_node_holds_is_dropped |
| T-168 | A relationship that is not an implementation is ignored | S-06 | D-08 | done | tests/test_scip_ingest.py::test_a_relationship_that_is_not_an_implementation_is_ignored |
| T-169 | A declared encoding beats the table | S-06 | D-08 | done | tests/test_scip_offsets.py::test_a_declared_encoding_beats_the_table |
| T-170 | A line splits on the newline alone | S-06 | D-08 | done | tests/test_scip_offsets.py::test_a_line_splits_on_newline_alone |
| T-171 | An astral character counts as two UTF-16 units | S-06 | D-08 | done | tests/test_scip_offsets.py::test_an_astral_character_counts_as_two_utf16_units |
| T-172 | An end before its start collapses rather than inverting | S-06 | D-08 | done | tests/test_scip_offsets.py::test_an_end_before_its_start_collapses_rather_than_inverting |
| T-173 | A multi-line deprecated range keeps its end line | S-06 | D-08 | done | tests/test_scip_read.py::test_a_multi_line_deprecated_range_keeps_its_end_line |
| T-174 | An occurrence with no range survives as no span | S-06 | D-08 | done | tests/test_scip_read.py::test_an_occurrence_with_no_range_survives_as_no_span |
| T-175 | A two-element range is not a range | S-06 | D-08 | done | tests/test_scip_read.py::test_a_two_element_range_is_not_a_range |
| T-176 | The definition role is one bit of many | S-06 | D-08 | done | tests/test_scip_read.py::test_the_definition_role_is_one_bit_of_many |
| T-177 | The typed range wins where both are set | S-06 | D-08 | done | tests/test_scip_read.py::test_the_typed_range_wins_where_both_are_set |
| T-178 | An empty index is not a SCIP index | S-06 | D-08 | done | tests/test_scip_run.py::test_an_empty_index_is_not_a_scip_index |
| T-179 | A missing index is refused rather than invented | S-06 | D-08 | done | tests/test_scip_run.py::test_an_index_that_is_not_there_is_refused_rather_than_invented |
| T-180 | An unknown indexer names the indexers this project knows | S-06 | D-08 | done | tests/test_scip_run.py::test_an_unknown_indexer_is_an_error_that_names_the_known_ones |
| T-181 | The SCIP capability table is per indexer and never per language | S-06 | D-08 | done | tests/test_scip_run.py::test_the_capability_table_is_per_indexer_and_never_per_language |
| T-182 | The overlay stays off unless the project asks | S-06 | D-08 | done | tests/test_scip_run.py::test_the_overlay_is_off_unless_the_project_asks |
| T-183 | A backtick-quoted name keeps its separators | S-06 | D-08 | done | tests/test_scip_symbol.py::test_a_backtick_quoted_name_keeps_its_separators |
| T-184 | A local symbol names nothing outside its document | S-06 | D-08 | done | tests/test_scip_symbol.py::test_a_local_symbol_names_nothing_outside_its_document |
| T-185 | An unset kind keeps whatever tree-sitter found | S-06 | D-08 | done | tests/test_scip_symbol.py::test_an_unset_kind_keeps_whatever_tree_sitter_found |
| T-186 | A parameter group is no part of the name | S-06 | D-08 | done | tests/test_scip_symbol.py::test_a_parameter_group_is_no_part_of_the_name |
| T-187 | A group wire type is refused rather than skipped | S-06 | D-08 | done | tests/test_scip_wire.py::test_a_group_wire_type_is_refused_rather_than_skipped |
| T-188 | A varint round trips through both halves | S-06 | D-08 | done | tests/test_scip_wire.py::test_a_varint_round_trips_through_both_halves |
| T-189 | The counts report the resolved share | S-07 | D-01 | done | tests/test_store.py::test_counts_report_the_resolved_share |
| T-190 | Deleting a file takes its FTS rows with it | S-07 | D-01 | done | tests/test_store.py::test_deleting_a_file_takes_its_fts_rows_with_it |
| T-191 | The unique key is the identifier range | S-07 | D-01 | done | tests/test_store.py::test_the_unique_key_is_the_identifier_range |
| T-192 | A bare verified mapping reads as a one-element list | S-11 | D-28 | done | tests/test_bundle.py::test_a_bare_verified_mapping_reads_as_a_one_element_list |
| T-193 | Every index gloss is the description of its concept -- dropped: the check went with `scripts/check_index_gloss.py` in `832b1bb` | S-11 | D-29 | dropped | tests/test_bundle.py::test_every_index_gloss_is_its_concepts_description |
| T-194 | A concept reads as reviewed only where a human stamped it | S-11 | D-28 | done | tests/test_bundle.py::test_a_concept_reads_as_reviewed_only_where_a_human_stamped_it |
| T-195 | The trust tier reads the three cases section 5.3 names | S-11 | D-28 | done | tests/test_bundle.py::test_the_trust_tier_reads_the_three_cases_section_5_3_names |
| T-196 | An unset watchdog interval sends no ping | S-09 | D-11 | done | tests/test_systemd.py::test_no_watchdog_means_no_pings |
| T-197 | The pet reaches the notify socket | S-09 | D-11 | done | tests/test_systemd.py::test_the_pet_reaches_the_notify_socket |
| T-198 | The watchdog directive has a keepalive | S-09 | D-11 | done | tests/test_systemd.py::test_the_watchdog_directive_has_a_keepalive |
| T-199 | A constructor resolves through the class, never through `__init__` | S-02 | D-03 | done | tests/test_resolve.py::test_a_constructor_resolves_through_the_class_and_never_through_init |
| T-200 | Both reach notices appear together | S-10 | D-11 | done | tests/test_partc.py::test_both_reach_notices_appear_together |
| T-201 | The graph notice reports what the graphrag CLI reports | S-10 | D-11 | done | tests/test_partc.py::test_the_graph_notice_reports_what_the_graphrag_cli_reports |
| T-202 | The code notice reports what the coderag CLI reports | S-10 | D-11 | done | tests/test_partc.py::test_the_code_notice_reports_what_the_coderag_cli_reports |
| T-203 | A clean stop precedes the start that is timed | S-09 | D-11 | done | tests/test_partc.py::test_a_clean_stop_precedes_the_start_that_is_timed |
| T-204 | The unit reports active only once healthz answers | S-09 | D-11 | done | tests/test_partc.py::test_the_unit_reports_active_only_once_healthz_answers |
| T-205 | The five real profiles carry one graphrag entry | S-10 | D-09 | done | tests/test_partc.py::test_the_five_real_profiles_carry_one_graphrag_entry |
| T-206 | The URL the profiles name answers | S-10 | D-09 | done | tests/test_partc.py::test_the_url_the_profiles_name_answers |
| T-207 | A taken port is refused by name | S-10 | D-06, D-09 | done | tests/test_partc.py::test_a_taken_port_is_refused_by_name |
| T-208 | An expression receiver leaves the repo rather than picking a homonym | S-14 | D-27 | done | tests/test_resolve.py::test_an_expression_receiver_leaves_the_repo_rather_than_picking_a_homonym |
| T-209 | The receipt on disk is attested | S-11 | D-30 | done | tests/test_attester.py::test_the_receipt_on_disk_is_attested |
| T-210 | A corrected citation is not a dropped source -- dropped: the check went with `scripts/check_no_shrink.py` in `832b1bb` | S-11 | D-31 | dropped | tests/test_bundle.py::test_a_corrected_citation_is_not_a_dropped_source |
| T-211 | A run on a dirty tree is rejected | S-11 | D-33 | done | tests/test_attester.py::test_a_run_on_a_dirty_tree_is_rejected |
| T-212 | A run whose assertions never ran is rejected | S-11 | D-33 | done | tests/test_attester.py::test_a_run_whose_assertions_never_ran_is_rejected |
| T-213 | A second concurrent run refuses rather than clobbers | S-11 | D-33 | done | tests/test_attester.py::test_a_second_concurrent_run_refuses_rather_than_clobbers |
| T-214 | A further save restarts the quiet window -- dropped: `D-48` deleted the quiet window in `a7a7884` | S-09 | D-32 | dropped | tests/test_watch.py::test_a_further_save_restarts_the_quiet_window |
| T-215 | An explicit call pulls a waiting job forward -- dropped: `D-48` deleted the quiet window in `a7a7884` | S-09 | D-32 | dropped | tests/test_watch.py::test_an_explicit_call_pulls_a_waiting_job_forward |
| T-216 | A hung search raises rather than scoring zero | S-11 | D-33 | done | tests/test_two_engine.py::test_a_hung_search_raises_rather_than_scoring_zero |
| T-217 | The probe covers every mode the run uses | S-11 | D-33 | done | tests/test_two_engine.py::test_the_probe_covers_every_mode_the_run_uses |
| T-218 | Prune removes the orphan directory and the count reaches zero | S-07 | D-34 | done | tests/test_registry.py::test_prune_removes_the_directory_so_the_count_reaches_zero |
| T-219 | A symlink enrols the project it points at | S-07 | D-35 | done | tests/test_discovery.py::test_a_symlink_enrols_the_project_it_points_at |
| T-220 | The resolved target is the key and never the link | S-07 | D-35 | done | tests/test_discovery.py::test_the_resolved_target_is_the_key_and_never_the_link |
| T-221 | Two links to one target are one member | S-07 | D-35 | done | tests/test_discovery.py::test_two_links_to_one_target_are_one_member |
| T-222 | A broken link is skipped and never registered | S-07 | D-35 | done | tests/test_discovery.py::test_a_broken_link_is_skipped_and_never_registered |
| T-223 | A symlink cycle terminates | S-07 | D-35 | done | tests/test_discovery.py::test_a_symlink_cycle_terminates |
| T-224 | federation_exclude matches the target and not only the link | S-07 | D-35 | done | tests/test_discovery.py::test_federation_exclude_matches_the_target_and_not_only_the_link |
| T-225 | A declared member survives the walk | S-07 | D-35 | done | tests/test_discovery.py::test_a_declared_member_survives_the_walk |
| T-228 | exclude removes a directory from the index pass | S-07 | D-36 | done | tests/test_discovery.py::test_exclude_removes_a_directory_from_the_index_pass |
| T-229 | exclude reaches the index through the project config | S-07 | D-36 | done | tests/test_discovery.py::test_exclude_reaches_the_index_through_the_project_config |
| T-230 | languages keeps only what the project names | S-07 | D-36 | done | tests/test_discovery.py::test_languages_keeps_only_what_the_project_names |
| T-231 | A walked tree honours exclude without git | S-07 | D-36 | done | tests/test_discovery.py::test_a_walked_tree_honours_exclude_without_git |
| T-232 | A deleted project loses its row | S-07 | D-37 | done | tests/test_prune.py::test_a_deleted_project_loses_its_row |
| T-233 | A removed parent keeps the row, which is the unmount case | S-07 | D-37 | done | tests/test_prune.py::test_a_removed_parent_keeps_the_row |
| T-234 | A project restored inside the grace period keeps the row | S-07 | D-37 | done | tests/test_prune.py::test_a_project_restored_inside_the_grace_period_keeps_the_row |
| T-235 | A removed link releases the claim and the target survives | S-07 | D-37 | done | tests/test_prune.py::test_a_removed_link_releases_the_claim_and_the_target_survives |
| T-236 | A removed link keeps a row another root claims | S-07 | D-37 | done | tests/test_prune.py::test_a_removed_link_keeps_a_row_another_root_claims |
| T-237 | A directly enrolled member survives its link | S-07 | D-37 | done | tests/test_prune.py::test_a_directly_enrolled_member_survives_its_link |
| T-238 | Nothing due reads no registry | S-07 | D-37 | done | tests/test_prune.py::test_nothing_due_reads_no_registry |
| T-239 | find_symbol spans the federation and names the project | S-07 | D-38 | done | tests/test_discovery.py::test_find_symbol_spans_the_federation_and_names_the_project |
| T-240 | An unindexed member is a gap and not an absence | S-07 | D-38 | done | tests/test_discovery.py::test_an_unindexed_member_is_a_gap_and_not_an_absence |
| T-241 | A row another process wrote reaches the watch set | S-09 | D-39 | done | tests/test_watch.py::test_a_row_written_by_another_process_reaches_the_watch_set |
| T-242 | An unmoved registry is stat'ed and not parsed | S-09 | D-39 | done | tests/test_watch.py::test_an_unmoved_registry_is_stat_ed_and_not_parsed |
| T-243 | A dead row takes its graph with it | S-07 | D-41 | done | tests/test_prune.py::test_a_dead_row_takes_its_graph_with_it |
| T-244 | A graph written inside the idle floor is left alone | S-07 | D-41 | done | tests/test_prune.py::test_a_graph_written_inside_the_idle_floor_is_left_alone |
| T-245 | Quarantine expires on its own clock | S-07 | D-41 | done | tests/test_prune.py::test_quarantine_expires_on_its_own_clock |
| T-246 | A failed quarantine never degrades to a delete | S-07 | D-41 | done | tests/test_prune.py::test_a_failed_quarantine_never_degrades_to_a_delete |
| T-247 | Quarantine is not counted as an orphan, and a prune refuses the wipe shape | S-07 | D-41 | done | tests/test_registry.py::test_quarantine_is_not_counted_as_an_orphan |
| T-248 | A deletion is not lost to a re-arm queued in the same pass | S-09 | D-42 | done | tests/test_watch.py::test_a_deletion_is_not_lost_to_a_rearm_queued_in_the_same_pass |
| T-249 | The watcher re-arms after an error instead of dying | S-09 | D-42 | done | tests/test_watch.py::test_the_watcher_rearms_after_an_error_instead_of_dying |
| T-250 | An unmounted volume is never read as a deletion | S-07 | D-43 | done | tests/test_prune.py::test_an_unmounted_volume_is_never_read_as_a_deletion |
| T-251 | A new graph can give its pages back | S-01 | D-44 | done | tests/test_store.py::test_a_new_graph_can_give_its_pages_back |
| T-252 | A reference survives a pass as a row carrying `receiver` and `is_member` | S-01 | D-45 | done | tests/test_resolvedb.py::test_a_reference_survives_a_pass_as_a_row |
| T-253 | An import survives a pass carrying its symbol, alias and raw module string | S-01 | D-45 | done | tests/test_resolvedb.py::test_an_import_survives_a_pass_as_a_row |
| T-254 | The two resolvers return identical candidates over this repo | S-01 | D-46 | done | tests/test_resolvedb.py::test_the_two_resolvers_agree_over_this_repo |
| T-255 | The enclosing query agrees with the extractor | S-01 | D-46 | done | tests/test_resolvedb.py::test_the_enclosing_query_agrees_with_the_extractor |
| T-258 | A name the other file defines still resolves | S-01 | D-46 | done | tests/test_resolvedb.py::test_a_name_the_other_file_defines_still_resolves |
| T-259 | A wider pool is ranked and never forced | S-01 | D-46 | done | tests/test_resolvedb.py::test_a_wider_pool_is_ranked_and_never_forced |
| T-263 | A file-local reference is an edge and a crossing one is a row | S-01 | D-46 | done | tests/test_resolvedb.py::test_a_file_local_reference_is_an_edge_and_a_crossing_one_is_a_row |
| T-264 | No stored edge crosses a file | S-01 | D-46 | done | tests/test_resolvedb.py::test_no_stored_edge_crosses_a_file |
| T-279 | Rewriting one file destroys no edge that names another file | S-01 | D-46 | done | tests/test_resolvedb.py::test_no_stored_edge_crosses_a_file |
| T-281 | An upgraded cross-file call is answered once | S-06 | D-46 | done | tests/test_scip_ingest.py::test_an_upgraded_cross_file_call_is_answered_once |
| T-256 | Editing one file rewrites that file's rows and no other file's | S-01 | D-47 | done | tests/test_perfile.py::test_editing_one_file_rewrites_that_file_and_no_other |
| T-257 | Every FTS posting names a live node, and every node has one | S-01 | D-47 | done | tests/test_perfile.py::test_every_posting_names_a_live_node_and_every_node_has_one |
| T-261 | A generated bundle is refused on its content and not its name | S-01 | D-47 | done | tests/test_perfile.py::test_a_generated_bundle_is_refused_on_its_content_and_not_its_name |
| T-262 | A kind no writer produces is not declared | S-01 | D-47 | done | tests/test_store.py::test_a_kind_no_writer_produces_is_not_declared |
| T-268 | Two overlapping identifier ranges are not both written | S-01 | D-47 | done | tests/test_perfile.py::test_two_overlapping_identifier_ranges_are_not_both_written |
| T-276 | A pass that rewrites part of the tree does not checkpoint | S-01 | D-47 | done | tests/test_perfile.py::test_a_pass_that_rewrites_part_of_the_tree_does_not_checkpoint |
| T-277 | A store an index pass creates can give its pages back | S-01 | D-47 | done | tests/test_perfile.py::test_a_store_this_engine_creates_can_give_its_pages_back |
| T-278 | A renamed symbol is not findable under its old name | S-01 | D-47 | done | tests/test_perfile.py::test_a_renamed_symbol_is_not_findable_under_its_old_name |
| T-280 | The file count is the tree's and carries no synthetic row | S-01 | D-47 | done | tests/test_perfile.py::test_the_file_count_is_the_tree_s_and_carries_no_synthetic_row |
| T-282 | A changed file makes one file parse, and not the tree | S-01 | D-47 | done | tests/test_index.py::test_a_changed_file_makes_the_pass_run |
| T-283 | Deleting a file takes its FTS rows through the pass path | S-01 | D-47 | done | tests/test_store.py::test_deleting_a_file_takes_its_fts_rows_with_it |
| T-260 | A submitted job is takeable at once | S-01 | D-48 | done | tests/test_watch.py::test_a_submitted_job_is_takeable_at_once |
| T-270 | The watcher hands the changed paths to the queue | S-01 | D-48 | done | tests/test_watch.py::test_the_watcher_hands_the_changed_paths_to_the_queue |
| T-285 | A hinted pass hashes the named paths and not the tree | S-01 | D-48 | done | tests/test_perfile.py::test_a_hinted_pass_hashes_the_named_paths_and_not_the_tree |
| T-286 | A hinted pass does not run the SCIP overlay, and an unhinted one does | S-01 | D-51 | done | tests/test_perfile.py::test_a_hinted_pass_does_not_run_the_scip_overlay |
| T-287 | A save is searchable before the next one lands, timed through the daemon | S-01 | D-48 | done | tests/test_freshness.py::test_a_save_is_searchable_before_the_next_one_lands |
| T-288 | The save-to-searchable receipt is attested, and a moved digit is refused | S-01 | D-48 | done | tests/test_freshness.py::test_the_freshness_receipt_is_attested |
| T-289 | The save-to-searchable concept renders every digit its receipt carries | S-01 | D-48 | done | tests/test_freshness.py::test_the_freshness_receipt_agrees_with_the_concept |
| T-271 | Two hinted submissions merge their paths | S-01 | D-48 | done | tests/test_watch.py::test_two_hinted_submissions_merge_their_paths |
| T-272 | A hint merged with a whole-tree job runs whole-tree | S-01 | D-48 | done | tests/test_watch.py::test_a_hint_merged_with_a_whole_tree_job_runs_whole_tree |
| T-273 | A hint over the cap falls back to the whole tree | S-01 | D-48 | done | tests/test_watch.py::test_a_hint_over_the_cap_falls_back_to_the_whole_tree |
| T-274 | An unhinted pass finds a change no event reported | S-01 | D-48 | done | tests/test_perfile.py::test_an_unhinted_pass_finds_a_change_no_event_reported |
| T-275 | The prune clock still ticks on an empty batch | S-01 | D-48 | done | tests/test_watch.py::test_the_prune_clock_still_ticks_on_an_empty_batch |
| T-284 | The queue merges a queued job and requeues a running one | S-01 | D-48 | done | tests/test_index.py::test_the_queue_merges_a_queued_job_and_requeues_a_running_one |
| T-290 | Every armed root delivers an event, and not only the first | S-01 | D-48 | done | tests/test_watch.py::test_every_armed_root_delivers_and_not_only_the_first |
| T-291 | A Go import drops the module path and meets its package directory | S-01 | D-40 | done | tests/test_resolve.py::test_a_go_import_drops_the_module_path_and_names_the_package_directory |
| T-292 | A PHP namespace meets the PSR-4 directory it maps to | S-01 | D-40 | done | tests/test_resolve.py::test_a_php_namespace_meets_the_psr4_directory_it_maps_to |
| T-293 | A TypeScript relative import meets the file it names | S-01 | D-40 | done | tests/test_resolve.py::test_a_typescript_relative_import_meets_the_file_it_names |
| T-294 | Two spellings never share one module name | S-01 | D-40 | done | tests/test_resolve.py::test_two_spellings_never_share_one_module_name |
| T-295 | No tracked file carries a banned name | S-01 | D-52 | done | tests/test_hygiene.py::test_no_tracked_file_carries_a_banned_name |
| T-296 | No tracked file carries a home path | S-01 | D-52 | done | tests/test_hygiene.py::test_no_tracked_file_carries_a_home_path |
| T-297 | A Go package receiver narrows to the package it names | S-01 | D-40 | done | tests/test_resolve.py::test_a_go_package_receiver_narrows_to_the_package_it_names |
| T-298 | A PHP class receiver narrows across the case PSR-4 drops | S-01 | D-40 | done | tests/test_resolve.py::test_a_php_class_receiver_narrows_across_the_case_psr4_drops |
| T-304 | The ban reads a name and its own capitalisation as one name | S-01 | D-52 | done | tests/test_hygiene.py::test_the_name_ban_folds_case |
| T-299 | Every reason a writer produces is declared | S-01 | D-53 | done | tests/test_store.py::test_every_reason_a_writer_produces_is_declared |
| T-300 | A language with no capability says so, and an empty file says something else | S-01 | D-53 | done | tests/test_index.py::test_a_language_with_no_capability_says_so |
| T-301 | A query that raises leaves the file saying so | S-01 | D-53 | done | tests/test_extract.py::test_a_query_that_raises_leaves_the_file_saying_so |
| T-302 | No file answers `none` without saying why | S-01 | D-53 | done | tests/test_index.py::test_no_file_answers_none_without_saying_why |
| T-265 | An indexer with no command is `manual` and never `absent` | S-01 | D-54 | done | tests/test_scip_run.py::test_an_indexer_with_no_command_is_manual_and_never_absent |
| T-266 | A command that runs lifecycle scripts is refused | S-01 | D-54 | done | tests/test_scip_deps.py::test_a_command_that_runs_lifecycle_scripts_is_refused |
| T-267 | A file edited after the artifact keeps its syntactic edge | S-01 | D-55 | done | tests/test_scip_ingest.py::test_a_file_edited_after_the_artifact_keeps_its_syntactic_edge |
| T-305 | `doctor` prints the SCIP readiness block | S-01 | D-54 | done | tests/test_tools.py::test_doctor_prints_the_scip_readiness_block |
| T-306 | A project with no build-unit marker is `unconfigured` | S-01 | D-54 | done | tests/test_scip_run.py::test_a_project_with_no_build_unit_marker_is_unconfigured |
| T-303 | `doctor` prints the file census, and `by_tier` sums to the file count | S-01 | D-53 | done | tests/test_index.py::test_the_census_counts_every_file_once, tests/test_tools.py::test_doctor_prints_the_file_census |
| T-307 | Every `done` row names a test that exists | S-18 | D-56 | done | tests/test_plan_pair.py::test_every_done_row_names_a_test_that_exists |
| T-308 | A foreign node is exempt and the exemption is counted | S-18 | D-56 | done | tests/test_plan_pair.py::test_a_foreign_node_is_exempt_and_the_exemption_is_visible |
| T-309 | A row naming no test node is `planned` | S-18 | D-56 | done | tests/test_plan_pair.py::test_a_row_with_no_node_is_planned |
| T-310 | Every test that exists is named by a row | S-18 | D-56 | done | tests/test_plan_pair.py::test_every_test_that_exists_is_named_by_a_row |
| T-311 | Every path a development row owns is tracked | S-18 | D-56 | done | tests/test_plan_pair.py::test_every_path_a_dev_row_owns_is_tracked |
| T-312 | Every row names at least one row in the other document | S-18 | D-56 | done | tests/test_plan_pair.py::test_every_row_names_at_least_one_row_in_the_other_document |
| T-313 | No ID is an orphan in either direction, and a range is expanded first | S-18 | D-56 | done | tests/test_plan_pair.py::test_no_id_is_an_orphan_in_either_direction |
| T-314 | A populated submodule is enumerated | S-12 | D-58 | done | tests/test_discover.py::test_a_populated_submodule_is_enumerated |
| T-315 | An empty submodule directory adds nothing | S-12 | D-58 | done | tests/test_discover.py::test_an_empty_submodule_directory_adds_nothing |
| T-316 | A nested submodule is reached | S-12 | D-58 | done | tests/test_discover.py::test_a_nested_submodule_is_reached |
| T-317 | An exclude still drops a submodule file | S-12 | D-58 | done | tests/test_discover.py::test_an_exclude_still_drops_a_submodule_file |
| T-318 | A member inherits the exclude of the root that claims it | S-07 | D-35 | done | tests/test_discovery.py::test_a_member_inherits_the_exclude_of_the_root_that_claims_it |
| T-319 | A member with its own config inherits nothing | S-07 | D-35 | done | tests/test_discovery.py::test_a_member_with_its_own_config_inherits_nothing |
| T-320 | An unclaimed project inherits nothing | S-07 | D-35 | done | tests/test_projcfg.py::test_an_unclaimed_project_inherits_nothing |
| T-321 | A member inherits the SCIP opt-in from the root that claims it | S-06 | D-08 | done | tests/test_projcfg.py::test_a_member_inherits_the_scip_opt_in_from_the_root_that_claims_it |
| T-322 | A member with its own config inherits no SCIP opt-in | S-06 | D-08 | done | tests/test_projcfg.py::test_a_member_with_its_own_config_inherits_no_scip_opt_in |
| T-323 | A build unit is every marker directory and never a vendored one | S-06 | D-08 | done | tests/test_scip_run.py::test_a_build_unit_is_every_marker_directory_and_never_a_vendored_one |
| T-324 | An indexer is skipped before it runs where the language is absent | S-06 | D-08 | done | tests/test_scip_run.py::test_an_indexer_is_skipped_before_it_runs_where_the_language_is_absent |
| T-325 | A sub-module is graded against its own files and not the whole tree | S-06 | D-08 | done | tests/test_scip_run.py::test_a_sub_module_is_graded_against_its_own_files_and_not_the_whole_tree |
| T-326 | The overlay writes its index beside the graph and never in the project | S-06 | D-08 | done | tests/test_scip_run.py::test_the_overlay_writes_its_index_beside_the_graph_and_never_in_the_project |
| T-327 | A unit with no marker has no plan | S-06 | D-54 | done | tests/test_scip_deps.py::test_a_unit_with_no_marker_has_no_plan |
| T-328 | A bad plan is refused where it is chosen and not where it was written | S-06 | D-54 | done | tests/test_scip_deps.py::test_a_bad_plan_is_refused_where_it_is_chosen_and_not_where_it_was_written |
| T-329 | The helper resolves nothing a project cannot use | S-06 | D-54 | done | tests/test_scip_deps.py::test_the_helper_resolves_nothing_a_project_cannot_use |
| T-330 | A progress file outlives its store and the prune sweeps it | S-07 | D-41 | done | tests/test_prune.py::test_a_progress_file_outlives_its_store_and_the_prune_sweeps_it |
| T-331 | A prune against an empty registry refuses | S-07 | D-41 | done | tests/test_registry.py::test_a_prune_against_an_empty_registry_refuses |
| T-332 | A prune over half the tree needs force | S-07 | D-41 | done | tests/test_registry.py::test_a_prune_over_half_the_tree_needs_force |
| T-333 | A worktree groups under the repository it belongs to | S-06 | D-57 | done | tests/test_scip_census.py::test_a_worktree_groups_under_the_repository_it_belongs_to |
| T-334 | A root reaches a receipt only as a digest | S-06 | D-57 | done | tests/test_scip_census.py::test_a_root_reaches_a_receipt_only_as_a_digest |
| T-335 | The overlay arm refuses every root that is not ready | S-06 | D-57 | done | tests/test_scip_census.py::test_the_overlay_arm_refuses_every_root_that_is_not_ready |
| T-336 | The share arm counts the stores it could not read | S-06 | D-57 | done | tests/test_scip_census.py::test_the_share_arm_counts_the_stores_it_could_not_read |
| T-337 | The arm list counts agree with the number it states | S-11 | D-12 | done | tests/test_bundle.py::test_the_arm_list_counts_agree_with_the_number_it_states |

`T-275` and `T-274` pass on the predecessor commit, and they are regression guards rather than
negative tests. `T-275` holds `yield_on_timeout=True`, which sits four lines from the deleted
window: the empty batch that flag produces is the only clock `prune.run_due` is measured against,
and nothing else calls it. `T-274` fails on the predecessor for the keyword alone, because that
pass reads the tree every time and the healing it asserts is what the pass already was. The other
seven fail there on the behaviour.

`T-285` is the second half of the plan's `T-270`: the watcher hands the paths over, and the pass
hashes those and not the tree. Two claims, so two cases, and the plan wrote them as one row.

`T-290` passes on the predecessor commit and is stated as a sentinel rather than a negative test.
Every other arm case watches one root, so no case in this suite could distinguish an arm that
watches all its roots from one that watches the first. That gap is what let
`defects/the-fleet-wide-arm-loses-roots.md` be filed against a working watcher and stand for a
day: the engine was right and nothing could say so. The row exists to fail the day the arm really
does lose a root. Its probe file is a `.py` on purpose — that defect's probe was a `.txt`, which
`watch._keep` refuses in every project, so it measured the filter and read the result as the arm.

`T-291`, `T-292` and `T-293` fail on the predecessor: both halves of the comparison were dotted
there, so a Go import path, a PHP namespace and a `./x` specifier each matched nothing a file
could define. `T-294` is the one of the four that passes on the predecessor and fails on the
first draft of `D-40`. Untagged, `Orders.php` and `orders.ts` in one directory resolved to the
same module and each file answered for the other's `Order`. The two-engine receipt read it as
precision 1.000 to 0.994, which is the only reason the tag exists.

`T-297` and `T-298` are the second half of `D-40`, and they exist because the first half broke
what it was fixing. A module name is no longer always dotted, and two sites still split one on a
dot to get its last segment — `resolve._receiver_modules` and `resolvedb.receiver_modules`. On
`package:internal/billing/rates` that split returns the whole string, so a Go receiver matched no
module at all and every member call on an imported package resolved `external`. Both fail on the
predecessor with `external: True` and an empty candidate list, and both pass once the split asks
the spelling for its own separator. `T-298` carries the case half: `module_name` lowercases a PSR-4
namespace and a PHP receiver is written in the class's own case, so the two never meet unfolded.

`T-295` and `T-296` widen the public-hygiene gate from `src/graphrag/*.py` to every tracked file
but one suffix: `tests/test_hygiene.py` holds `_UNSCANNED = (".lock",)`, because a lock file is a
resolver's transcript of public package names and is the one tracked file whose contents nobody
wrote.
Both fail on the predecessor with the ban populated, and both are unreachable there without it:
CI set `GRAPHRAG_NAME_BAN` to `none`, so the ban had never held a name and had never rejected
anything. `T-295` found 70 occurrences across 23 files and `T-296` found one home path in
`scripts/`, neither of which the old `src/`-only glob could see.

`T-304` is the defect in the gate the other two rows arm. Both matched with a case-sensitive
`in`, which reads a name and its own capitalisation as two different names, so the widened glob
still shipped two names the list already held — one camel-cased inside a longer identifier, one
upper-cased as an environment variable. It fails on the predecessor because `_hits` does not exist
there and the comparison it replaces returns no match on either. The case that grades it names
neither leak: this file is tracked, and `T-295` reads it.

`T-299` through `T-303` are six cases for five rows, and all six fail on the predecessor
`1dd0fe9` — the whole selection, not a subset. Each fails for its own reason and not for a shared
import error: `T-299` on `store.REASONS` not existing, `T-301` on `_run` swallowing the query error
and leaving a `[]` byte-identical to a clean parse, `T-300` and `T-302` on `sqlite3` refusing a
column named `reason`, `T-303`'s store half on `store.census` not existing and its doctor half on
`cmd_doctor` having no `files` key.

`T-299` is the mirror of `T-262`, which grades `store.NODE_KINDS` from the other direction, and it
reads the writers rather than restating them: a set and a copy of itself agree about everything.
Three modules assign a reason, in three syntactic shapes — an attribute assignment, a keyword
argument, and the pair `_tier` returns — so the helper walks the AST for all three. The design's
sixth value `not_parsed` was dropped by this case before it shipped: `filters.indexable` refuses a
path whose language is empty, so every target reaches `extract` and carries facts, and a declared
value no writer produces is a filter a reader writes against nothing.

`T-302` asserts the invariant as the query an operator would actually run, which is what makes it
the row the fleet reindex is graded by rather than a restatement of `T-300`.

`T-286` fails on the predecessor commit with one failure, on the first assertion: the overlay ran on
a hinted pass. The reading behind it is in `defects/the-overlay-ran-on-every-save.md`.

`T-287` is opt-in and skips by default, because it needs a real repository, an editor-shaped save
and the daemon holding the writer lock. Name the root and the file in the environment. A fixture
would grade a different code path from the one a save takes, and the claim is about the save.

`T-288` and `T-289` grade the receipt `T-287` writes, and they are not opt-in. They skip only where
no receipt is on disk. `T-289` is the sibling of `T-123`: it holds every digit the concept prints
to the run that produced it, so a prose figure cannot drift away from a measurement. Neither case
can pass on the predecessor commit, which carries no attester and no concept file.

`T-284` records an edited test rather than a new one. The queue verdict `dropped` became `merged`,
because dropping a second submission was correct only while a job meant *reindex everything*.

`T-277` and `T-280` pass on the predecessor commit, and they are regression guards rather than
negative tests. `D-44` bought the `auto_vacuum` pragma and `D-46` removed the synthetic
`<external>` file row, so both properties were already true before `D-47`. What they add is the
tier: `T-251` grades the pragma on a bare `store.connect`, and `T-277` grades it on a store a real
index pass created.

`T-257` was written as a row count first, and a row count cannot fail. `count(*)` on an
external-content FTS5 table reads `nodes`, so it agrees with itself whatever the index holds, and
FTS5's own `'integrity-check'` grades internal consistency and not the content table. Both passed
against a build with the per-file delete removed. The assertion reads the postings through
`fts5vocab` instead, and that build reds it.

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

**J-06 Re-index after one edit.** Change one file and wait for the watcher. Acceptance: one index
pass is queued for the one project, and the progress file names it.

**J-07 Route two questions unprompted.** From a fresh session, ask a meaning question. Then ask a
caller question. Acceptance: each reaches the engine the routing rule names, with neither engine
named in the prompt. Run 2026-08-27, two headless sessions under `claude -p`, neither prompt
naming an engine. The receipt is `j07-routing-selection.json` under the receipt directory, and it
carries both prompts and both tool sequences.

The meaning question called `mcp__coderag__search` in semantic mode, then read the file it named.
The caller question called `mcp__coderag__search` in lexical mode to name the symbol, then
`mcp__graphrag__neighbors` with `question=callers` to walk the edges from it. That is the
widen-then-confirm order, selected and not prompted.

`scripts/headless_probe.py` wrote that receipt out of the session's own tool stream, and `T-127`
grades it. A summary typed afterwards is a claim about the run rather than the run.

**J-08 Measure the two engines against each other.** Run a caller-question set against both. Score
both against hand-verified edges. Acceptance: the numbers exist and are recorded. Measured
2026-08-27 on this repo at commit `e76487a`: graphrag F1 0.879, coderag lexical 0.470, coderag
semantic 0.346, over ten questions. The result graduates to `knowledge/computations/`.

The class split is the part a single number hides, and this journey reports both. A name called only
through its own module scores 1.000 on precision and recall. A name the tree also carries as an
attribute scores 0.620 on precision. That second figure was 0.412 before `D-19` captured the
receiver, and what remains is a receiver naming a local variable.

The ground truth is read by hand, so a commit that adds a caller makes it stale. `T-123` reds when
that happens, and the repair is to read the new caller and add it to the row.

Only the graph figures are held to the prose, by `T-123`. The two retrieval arms move between runs
on one tree, because the coderag index reindexes under them. So their digits are dated by the run
above and are not graded.

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

- `tests/fixtures/wave1/` — `orders.py`, `orders.ts` and `Orders.php`. Three of the five wave-one
  languages carry a file. Each holds a class, a method, a member call, a static call and four
  import shapes. `javascript` and `tsx` carry none, and `T-04` covers the query they share with
  TypeScript. One directory rather than one per language, because the goldens are read side by side.
- The C gap has no directory. `tests/test_tools.py` builds `main.c` inline as `NO_CALLS`, and
  `T-14` and `T-64` read it. `tests/test_grammars.py` asserts the missing capability itself.
- The cycle fixture is three modules importing each other, built by the `repo` factory in
  `tests/test_index.py` rather than by a checked-in directory. It is five lines per module, and
  a directory on disk would hide them from the case that reads them.
- The non-ASCII identifier has no directory either. `tests/test_scip_offsets.py` holds the source
  inline as `SRC`, and `T-18` reads it against both column encodings.
- The CPython standard library at `v3.12.7`, cloned once into `~/.cache/graphrag/corpus`, for
  `T-07`. The case is marked `corpus` and skips when the clone is absent, so a fresh machine runs
  the suite without a network fetch. `GRAPHRAG_CORPUS_DIR` and `GRAPHRAG_CORPUS_REF` move it.

# Traceability

Every `T-nn` names exactly one `S-nn` and at least one `D-nn`. Every `D-nn` names at least one
`T-nn`. An ID is never reused and never deleted.

Seven checks, and they are a test: `tests/test_plan_pair.py`. A shell copy ran in the pre-push
gate until 2026-08-29, the six-rule ruling deleted it, and both documents went on describing it.
What that bought is `knowledge/defects/the-plan-pair-described-a-gate-that-was-gone.md`: six `done`
rows outliving their tests, three owned paths outliving their files, and 26 tests no row named.

Collection is an AST walk over `tests/test_*.py` and not `pytest --collect-only`. No row carries a
`[case]` suffix, so real collection would name nothing the walk does not, and a pytest run inside a
pytest run costs a second import of the whole suite.

A blank node cell is a finding unless the row is `planned`. It used to be skipped outright, and one
row of 122 was then the only row the check could not see.

A `(ccw)` node ID or path is exempt, because that test lives in another checkout and this runner
cannot reach it. The exemption is counted rather than waved through: a run finding none of them
fails, because an escape hatch nobody can size is a hole.

The orphan check expands a range before it resolves an ID. Eight dev rows write `T-94..T-101`, and
a token grep recovers only the two ends of one. The six interior IDs went unchecked.

Coverage runs in both directions, because a row naming nothing at all has no ID for an orphan check
to resolve. `(deletion)` is its one marked exemption, and `D-50` is the only row carrying it: a
symbol that was written and never read leaves no behaviour to grade, and a test asserting a private
name stays absent would be a worse liability than the row.

The backward direction is Part B rule 5. It found 63 of 181 collected functions named by no row in
the reconciliation that wrote `T-129` to `T-191`, and 26 more when it was written as a test.

The dead-path side resolves a directory anchor as well as a file. `src/graphrag/queries/imports/`
is tracked as the files under it and never as itself, so an exact-set compare read every directory
row as dead. The tree side is `git ls-files` rather than a walk, because the gate is about what a
clone gets.


# A correction `D-07` forced, 2026-08-27

`T-16` read *One edit reparses one file*, and `J-06` accepted on the progress file showing one file
reparsed. Both were wrong about this engine, so both are corrected here rather than left standing.

Resolution is global. A reference is scored against the whole symbol table, so a pass that reparsed
only the edited file would price every other file as a repo that does not define the name. `_facts`
therefore parses the whole tree whenever the content hash of any file moved. Per-file facts are not
persisted, so there is nothing to reuse.

What the watcher does hold is the property the row was reaching for: an edit to two files inside one
debounce window raises **one** index pass for the one project, never one per file. That is what
`T-16` asserts now, and what `J-06` accepts on.

`T-68` records a defect the case found. `ledger.append` stamped `ts` rounded to a millisecond, and
`read` sorted `reverse=True`. A stable sort hands back the older of a tied pair first, so the newest
row was not first. The stamp now carries full precision and the sort reverses an ascending result.

# What `T-204` found, 2026-08-27

`T-26` reads the unit text and finds `Type=notify`. It starts nothing, so it graded the directive
and never the ordering the directive is bought for.

`T-204` starts the unit and asks `/healthz` once, on the first `active` sample. Two of four starts
were refused, and one of the two stayed refused for 2.6 seconds. uvicorn runs the ASGI lifespan
before it binds the listening socket, and `READY=1` is sent from inside that lifespan.

`server.listen` binds and listens before uvicorn runs, so the socket exists before systemd is told
anything. Four of four starts then answered on the first sample. The same bind retires the
check-then-bind race that `port_free` left open in the collision guard.

# What `T-211` to `T-213` found, 2026-08-27

The two-engine receipt on disk carried `f1_lexical: 0.0` and `f1_semantic: 0.0` against a concept
claiming `0.412` and `0.312`. Neither arm regressed. `coderag_files` returned an empty set on a
failed `coderag search`, and an empty set scores `f1 = 0.0`, so an unreachable daemon read as a
measurement. The `shutil.which` skip guard proved the CLI was installed and never that the daemon
answered, which is the exact case the skip was written for.

The same receipt carried `f1_graph_distinctive: 0.987` from a run whose `distinctive["precision"]
== 1.0` assertion had failed, because the receipt is written before the assertions. `T-212` is what
stops that artifact grading as a measurement.

A serialized run on the committed tree settles it: 0.510 lexical and 0.316 semantic, and neither is
zero. The arms move a little between runs, so the concept carries the latest pair and names its
commit in the footnote.

`T-216` closes the last shape of the same hole. An error exit now raises, and so does unparsable
output, but a daemon that accepts the connection and never answers hung the measurement instead.
`SEARCH_TIMEOUT_S` bounds each search, and the timeout raises the way the other two do.

The graph figure moved for a reason the `commit_sha` field hid. The test reindexes the working tree,
and an uncommitted `extract.py` had gained a call to `grammars.capabilities`. The TRUTH row for that
symbol named six caller files and the tree held seven, so the seventh priced as a false positive.
The row now names `src/graphrag/extract.py`. `T-211` is what refuses a run over a tree the SHA does
not describe.

`T-265`, `T-266`, `T-305` and `T-306` grade the report before anything acts on it, and three of the
four read the shipped table rather than a list beside them. `T-265` asserts that the set of
indexers `readiness` calls `manual` is exactly the set whose command tuple is empty, with
`shutil.which` stubbed to fail everywhere so that `manual` is being decided ahead of `absent` and
not merely alongside it. `T-266` runs its guard over every argv in `deps.PLANS`, so a plan added
without `--ignore-scripts` fails at collection and not in a subprocess that has already fetched
and executed something; its second case replaces the shipped row with an unguarded one and asserts
`plan` refuses it, which is what proves the guard runs where the command is chosen.

`T-306` is the row a fleet measurement bought. The first draft of the tier called 121 TypeScript
roots `installable`; 119 of them hold no `tsconfig.json` at all, and `run.units` returning `[""]`
for "no marker found" is indistinguishable from `[""]` for "no marker needed". The case asserts
both readings from one project, before and after the marker is written.

`T-267` is graded against itself rather than against a literal. The same artifact is ingested
twice over the same store, with one file's mtime moved past the artifact's between the two runs:
one call rewritten, then none. On the predecessor the second run rewrites the call as well —
`calls == 1` where this reads `0` — so the failure is behavioural and not the missing `stale`
field, which was confirmed by re-running the case with that field's two assertions removed.

The four `T-266` cases fail on the predecessor as one collection error, because
`graphrag.scip.deps` is the change. The other four rows fail there each for their own reason:
`run.shutil` is absent for `T-265` and `T-306`, `IngestReport.stale` for `T-267`, and `doctor`
carries no `scip` key for `T-305`.
