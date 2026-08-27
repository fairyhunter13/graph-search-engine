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
| T-193 | Every index gloss is the description of its concept | S-11 | D-29 | done | tests/test_bundle.py::test_every_index_gloss_is_its_concepts_description |
| T-194 | The bundle reads as machine-confirmed and never as reviewed | S-11 | D-28 | done | tests/test_bundle.py::test_the_bundle_reads_as_machine_confirmed_and_never_as_reviewed |
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
| T-210 | A corrected citation is not a dropped source | S-11 | D-31 | done | tests/test_bundle.py::test_a_corrected_citation_is_not_a_dropped_source |
| T-211 | A run on a dirty tree is rejected | S-11 | D-33 | done | tests/test_attester.py::test_a_run_on_a_dirty_tree_is_rejected |
| T-212 | A run whose assertions never ran is rejected | S-11 | D-33 | done | tests/test_attester.py::test_a_run_whose_assertions_never_ran_is_rejected |
| T-213 | A second concurrent run refuses rather than clobbers | S-11 | D-33 | done | tests/test_attester.py::test_a_second_concurrent_run_refuses_rather_than_clobbers |
| T-214 | A further save restarts the quiet window | S-09 | D-32 | done | tests/test_watch.py::test_a_further_save_restarts_the_quiet_window |
| T-215 | An explicit call pulls a waiting job forward | S-09 | D-32 | done | tests/test_watch.py::test_an_explicit_call_pulls_a_waiting_job_forward |

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

Five checks, run by the pre-push gate. Silence is the pass. The hook is the copy that runs, and
this is its shape.

```sh
# A dead path, per path. A `(ccw)` token marks a row's foreign paths, and the skip is
# per entry, so an in-repo path beside one is still checked.
awk -F'|' '/^\| D-[0-9]/ {n = split($5, a, ","); for (i = 1; i <= n; i++) {
  gsub(/^[ \t]+|[ \t]+$/, "", a[i]); if (a[i] != "") print a[i] }}' docs/development-plan.md \
  | while IFS= read -r p; do
      case "$p" in '('*) continue ;; esac
      [ -n "$(git ls-files -- "$p")" ] || echo "dead path: $p"
    done

# An uncollected test node ID.
uv run pytest --collect-only -q -o addopts= | sort > /tmp/collected
grep -E '^\| T-[0-9]' docs/test-plan.md | while IFS='|' read -r _ id _ _ _ status node; do
  node="${node//[ |]/}"; status="${status// /}"
  if [ -z "$node" ]; then
    [ "$status" = planned ] || echo "${id// /}: no test node ID, and the row is not planned"
    continue
  fi
  [ "${node#'(ccw)'}" != "$node" ] && continue
  grep -qF "$node" /tmp/collected || echo "uncollected test: $node"
done

# An orphan ID, both directions. `T-94..T-101` is a range, and the hook expands it
# before resolving each ID to a row of its own in the other document.
plan_ids docs/test-plan.md D | while IFS= read -r id
do
  grep -qE "^\| $id \|" docs/development-plan.md || echo "orphan $id"
done

# Coverage. A row that names no ID at all resolves nothing, so the arm above never sees it.
grep -E '^\| D-[0-9]' docs/development-plan.md | grep -vE 'T-[0-9]'
grep -E '^\| T-[0-9]' docs/test-plan.md | cut -d'|' -f5 | grep -vE 'D-[0-9]'

# A collected test no row names. The `[case]` suffix goes first, or every
# parametrised test reads as unrecorded.
awk -F'|' '/^\| T-[0-9]/ { gsub(/[ \t]/, "", $7); if ($7 != "") print $7 }' \
  docs/test-plan.md | sort -u > /tmp/rows
grep '::' /tmp/collected | sed 's/\[.*\]//' | sort -u | comm -23 - /tmp/rows
```

`-o addopts=` is load-bearing. This repo sets `-q` there, and a second `-q` collapses collection to
a per-file count with no node ID in it. Every anchored row then reads as uncollected.

The dead-path side is `git ls-files -- "$p"` per path, never `grep -vFx` against one dump. The dump
form matches a whole line. A directory anchor such as `src/graphrag/queries/imports/` never appears
in it, so every directory row read as dead.

The match on the test side is `grep -qF` per row rather than `comm -23` over two sorted lists. A
collected line carries text around the node ID. An exact-line compare therefore reports a row the
runner does collect.

**A blank node cell is a finding unless the row is `planned`.** It used to be skipped outright. One
row of 122 was then the only row the check could not see.

A `(ccw)` node ID is skipped, for the reason a `(ccw)` path is. That test lives in another checkout
and this runner cannot collect it.

The orphan check expands a range before it resolves an ID. Eight dev rows write `T-94..T-101`, and
a token grep recovers only the two ends of one. The six interior IDs went unchecked.

The fourth check is coverage rather than a dangling reference. A row naming nothing at all passes
an orphan check, because it has no ID to resolve. It runs in both directions.

The fifth check runs the anchor check backwards. Part B rule 5 makes a test no row names a finding.
Only the row-to-test direction was gated, so 63 of 181 collected functions were named by no row.
The reconciliation pass wrote `T-129` to `T-191` for them.

The pattern is `T-[0-9]`, never a bare `T-`, so the vocabulary block above is not read as a row.
The tree side is `git ls-files` rather than a walk, because the gate is about what a clone gets.


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

A serialized run on the committed tree settles it: 0.535 lexical and 0.331 semantic, and neither is
zero. The concept now carries those figures, and its footnote names the run.

The graph figure moved for a reason the `commit_sha` field hid. The test reindexes the working tree,
and an uncommitted `extract.py` had gained a call to `grammars.capabilities`. The TRUTH row for that
symbol named six caller files and the tree held seven, so the seventh priced as a false positive.
The row now names `src/graphrag/extract.py`. `T-211` is what refuses a run over a tree the SHA does
not describe.
