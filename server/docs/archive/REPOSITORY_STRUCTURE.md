# Complete Repository Structure

```
trading-ai-extension/
├── server/
│   ├── app.py
│   │   ├── function: startup_event()
│   │   ├── class: AskResponse(BaseModel)
│   │   ├── function: root()
│   │   ├── function: analyze_chart()
│   │   ├── function: get_prompt()
│   │   ├── function: ask_about_chart()
│   │   ├── function: get_budget()
│   │   ├── function: get_models()
│   │   ├── class: SessionCreate(BaseModel)
│   │   ├── class: SessionUpdate(BaseModel)
│   │   ├── function: list_sessions()
│   │   ├── function: create_session()
│   │   ├── function: get_session()
│   │   ├── function: update_session()
│   │   ├── function: delete_session()
│   │   ├── function: get_session_memory()
│   │   ├── function: update_session_memory()
│   │   ├── class: HybridResponse(BaseModel)
│   │   ├── function: hybrid_endpoint()
│   │   ├── function: clear_hybrid_cache()
│   │   └── function: log_request_time()
│   ├── cache.py
│   │   └── class: SessionCache
│   ├── decision.py
│   │   └── function: get_base_prompt()
│   ├── hybrid_pipeline.py
│   │   └── function: hybrid_reasoning()
│   ├── openai_client.py
│   │   ├── function: enforce_budget()
│   │   ├── function: add_cost()
│   │   ├── function: get_budget_status()
│   │   ├── class: OpenAIClient
│   │   ├── function: get_client()
│   │   ├── function: list_available_models()
│   │   ├── function: resolve_model()
│   │   └── function: sync_model_aliases()
│   ├── requirements.txt
│   ├── ai/
│   │   ├── __init__.py
│   │   └── intent_analyzer.py
│   │       ├── function: get_client()
│   │       ├── function: load_intent_prompt()
│   │       └── function: analyze_intent()
│   ├── amn_teaching/
│   │   ├── __init__.py
│   │   ├── annotator_stub.py
│   │   │   └── function: draw_annotations()
│   │   ├── dataset_compiler.py
│   │   │   └── function: compile_master_dataset()
│   │   ├── teach_utils.py
│   │   │   ├── function: create_baseline_teaching_stub()
│   │   │   └── function: update_teaching_example()
│   │   └── routes.py
│   │       ├── function: list_examples()
│   │       └── function: update_example()
│   ├── chart_reconstruction/
│   │   ├── __init__.py
│   │   ├── data_utils.py
│   │   │   └── function: fetch_price_data()
│   │   ├── render_charts.py
│   │   │   └── function: render_all()
│   │   ├── renderer.py
│   │   │   ├── function: render_trade_chart()
│   │   │   └── function: create_summary_chart()
│   │   └── routes.py
│   │       ├── function: get_data_path()
│   │       └── function: get_chart_metadata()
│   ├── config/
│   │   ├── chart_patterns.json
│   │   └── intent_prompt.txt
│   ├── copilot_bridge/
│   │   ├── __init__.py
│   │   ├── performance_sync.py
│   │   │   ├── function: load_json()
│   │   │   └── function: summarize_performance()
│   │   └── routes.py
│   │       ├── function: get_performance()
│   │       ├── function: get_examples()
│   │       └── function: get_example()
│   ├── data/
│   │   ├── amn_training_examples/
│   │   ├── chart_metadata.json
│   │   ├── charts/
│   │   ├── conversation_log.json
│   │   ├── imported_trades.json
│   │   ├── last_deleted_trade.json
│   │   ├── ordered_charts/
│   │   ├── performance_logs.json
│   │   ├── retry_queue.json
│   │   ├── session_contexts.json
│   │   ├── trade_list_cache.json
│   │   ├── Trading-Images/
│   │   ├── training_dataset.json
│   │   └── user_profile.json
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── context_manager.py
│   │   │   ├── function: get_current_trade_index()
│   │   │   ├── function: set_current_trade_index()
│   │   │   ├── function: increment_trade_index()
│   │   │   ├── function: decrement_trade_index()
│   │   │   └── function: reset_trade_index()
│   │   ├── routes.py
│   │   │   ├── class: MessageSave(BaseModel)
│   │   │   ├── class: SessionSave(BaseModel)
│   │   │   ├── class: CommandRequest(BaseModel)
│   │   │   ├── function: get_status()
│   │   │   ├── function: save_message()
│   │   │   ├── function: load_session()
│   │   │   ├── function: save_session()
│   │   │   ├── function: clear_memory()
│   │   │   └── function: system_command()
│   │   ├── system_commands.py
│   │   │   ├── function: normalize_input()
│   │   │   ├── function: detect_command()
│   │   │   ├── function: execute_command()
│   │   │   ├── function: execute_stats_command()
│   │   │   ├── function: execute_delete_last_command()
│   │   │   ├── function: execute_restore_last_command()
│   │   │   ├── function: execute_clear_memory_command()
│   │   │   ├── function: execute_model_info_command()
│   │   │   ├── function: execute_list_sessions_command()
│   │   │   ├── function: execute_switch_session_command()
│   │   │   ├── function: execute_create_session_command()
│   │   │   ├── function: execute_delete_session_command()
│   │   │   ├── function: execute_rename_session_command()
│   │   │   ├── function: execute_open_teach_copilot_command()
│   │   │   ├── function: execute_close_teach_copilot_command()
│   │   │   ├── function: execute_show_chart_command()
│   │   │   ├── function: execute_help_command()
│   │   │   ├── function: execute_close_chat_command()
│   │   │   ├── function: execute_open_chat_command()
│   │   │   ├── function: execute_minimize_chat_command()
│   │   │   ├── function: execute_resize_chat_command()
│   │   │   ├── function: execute_reset_chat_size_command()
│   │   │   ├── function: execute_show_session_manager_command()
│   │   │   ├── function: execute_view_lessons_command()
│   │   │   ├── function: execute_view_lesson_command()
│   │   │   ├── function: execute_delete_lesson_command()
│   │   │   ├── function: execute_edit_lesson_command()
│   │   │   ├── function: execute_teaching_progress_command()
│   │   │   ├── function: execute_start_teaching_command()
│   │   │   ├── function: execute_end_teaching_command()
│   │   │   ├── function: execute_list_trades_command()
│   │   │   ├── function: execute_next_trade_teaching_command()
│   │   │   ├── function: execute_previous_trade_teaching_command()
│   │   │   ├── function: execute_skip_trade_teaching_command()
│   │   │   ├── function: execute_delete_trade_command()
│   │   │   ├── function: execute_view_trade_command()
│   │   │   └── function: execute_close_chart_command()
│   │   └── utils.py
│   │       ├── function: ensure_data_directory()
│   │       ├── function: load_json()
│   │       ├── function: save_json()
│   │       ├── function: initialize_default_files()
│   │       ├── function: get_memory_status()
│   │       └── function: save_session_context()
│   ├── performance/
│   │   ├── __init__.py
│   │   ├── dashboard.py
│   │   │   └── function: dashboard_data()
│   │   ├── learning.py
│   │   │   ├── function: _load_json()
│   │   │   └── function: generate_learning_profile()
│   │   ├── models.py
│   │   │   ├── class: TradeRecord(BaseModel)
│   │   │   ├── class: TradeUpdate(BaseModel)
│   │   │   └── class: PerformanceStats(BaseModel)
│   │   ├── routes.py
│   │   │   ├── function: log_trade()
│   │   │   ├── function: update_trade_route()
│   │   │   ├── function: get_stats()
│   │   │   ├── function: get_trades()
│   │   │   ├── function: get_all()
│   │   │   ├── function: get_trade()
│   │   │   ├── function: delete_trade_route()
│   │   │   └── function: backtest_chart_route()
│   │   └── utils.py
│   │       ├── function: ensure_data_dir()
│   │       ├── function: read_logs()
│   │       ├── function: invalidate_logs_cache()
│   │       ├── function: write_logs()
│   │       ├── function: _parse_timestamp()
│   │       ├── function: normalize_trade()
│   │       ├── function: save_trade()
│   │       ├── function: update_trade()
│   │       ├── function: get_trade_by_session()
│   │       ├── function: get_trade_by_id()
│   │       ├── function: calculate_stats()
│   │       ├── function: backtest_chart()
│   │       ├── function: get_all_trades()
│   │       └── function: delete_trade()
│   ├── routers/
│   │   ├── __init__.py
│   │   └── teach_router.py
│   │       ├── class: LessonRecord(BaseModel)
│   │       ├── function: start_teaching()
│   │       ├── function: next_trade()
│   │       ├── function: record_lesson()
│   │       ├── function: flag_invalid()
│   │       ├── function: end_teaching()
│   │       ├── function: get_teaching_status()
│   │       ├── function: teach_stream()
│   │       ├── function: preview_overlay()
│   │       ├── function: skip_trade()
│   │       ├── function: list_lessons()
│   │       ├── function: get_lesson()
│   │       ├── function: get_teaching_progress()
│   │       ├── function: delete_lesson()
│   │       └── function: update_lesson()
│   ├── static/
│   │   ├── dashboard.html
│   │   ├── teach.html
│   │   └── view_trades.html
│   ├── trades_import/
│   │   ├── __init__.py
│   │   ├── merge_utils.py
│   │   │   ├── function: merge_trade_by_id()
│   │   │   ├── function: batch_merge_trades()
│   │   │   └── function: auto_merge_all()
│   │   ├── parser.py
│   │   │   └── function: import_csv()
│   │   └── routes.py
│   │       ├── function: import_trades()
│   │       ├── function: list_imported_trades()
│   │       ├── function: get_import_stats()
│   │       ├── function: merge_trade()
│   │       └── function: batch_merge()
│   ├── trades_merge/
│   │   ├── __init__.py
│   │   ├── merge_utils.py
│   │   │   ├── function: load_json()
│   │   │   ├── function: save_json()
│   │   │   ├── function: merge_trade_by_id()
│   │   │   ├── function: auto_merge_all()
│   │   │   └── function: get_merge_preview()
│   │   ├── vision_linker.py
│   │   │   └── function: find_chart_for_trade()
│   │   └── routes.py
│   │       ├── function: auto_merge()
│   │       ├── function: merge_trade()
│   │       └── function: preview_merge()
│   └── utils/
│       ├── __init__.py
│       ├── chart_service.py
│       │   ├── function: _load_patterns()
│       │   ├── function: _normalize_to_filename()
│       │   ├── function: get_chart_url_fast()
│       │   ├── function: resolve_chart_filename()
│       │   ├── function: get_chart_url()
│       │   └── function: load_chart_base64()
│       ├── command_extractor.py
│       │   ├── function: extract_commands_from_response()
│       │   └── function: normalize_command()
│       ├── command_router.py
│       │   ├── function: validate_command_schema()
│       │   ├── function: fill_missing_fields()
│       │   ├── function: merge_multi_commands()
│       │   ├── function: route_command()
│       │   └── function: generate_execution_summary()
│       ├── command_schema.py
│       │   ├── class: CommandModel(BaseModel)
│       │   └── function: validate_command_schema()
│       ├── file_ops.py
│       │   ├── function: load_json()
│       │   ├── function: save_json()
│       │   └── function: append_json()
│       ├── gpt_client.py
│       │   ├── function: extract_bos_poi()
│       │   └── function: _regex_extract_bos_poi()
│       ├── overlay_drawer.py
│       │   ├── function: find_chart_image()
│       │   ├── function: draw_overlay_from_labels()
│       │   └── function: get_overlay_url()
│       ├── teach_parser.py
│       │   ├── function: normalize_number()
│       │   ├── function: extract_reason()
│       │   ├── function: update_partial_lesson()
│       │   ├── function: build_clarifying_question()
│       │   └── function: get_missing_fields()
│       └── trade_detector.py
│           ├── function: extract_trade_id_from_text()
│           ├── function: detect_trade_reference()
│           └── function: load_chart_image_for_trade()
├── visual-trade-extension/
│   ├── background.js
│   ├── manifest.json
│   ├── README.md
│   ├── content/
│   │   ├── content.js
│   │   ├── idb.js
│   │   └── overlay.css
│   ├── icons/
│   │   ├── icon128.png
│   │   ├── icon16.png
│   │   └── icon48.png
│   └── popup/
│       ├── popup.css
│       ├── popup.html
│       ├── popup.js
│       ├── teach.css
│       ├── teach.html
│       └── teach_panel.js
├── docs/
│   ├── DEVELOPMENT_CONTEXT.md
│   ├── SRS.md
│   ├── Screenshot 2025-10-27 213538.png
│   ├── Screenshot 2025-10-27 214351.png
│   ├── Tests 5F.1/
│   ├── Tests 5F.2/
│   └── Tests 5F.2 Fix/
├── tests/
│   ├── test_command_router.py
│   ├── test_commands_router.py
│   ├── test_intent_analyzer.py
│   ├── test_phase5e_comprehensive.py
│   ├── test_phase5e1_verification.py
│   └── test_phase5f1_verification.py
├── restart_server.py
│   ├── function: get_server_processes()
│   ├── function: kill_server_processes()
│   ├── function: start_server()
│   └── function: main()
├── run_server.py
│   ├── function: setup_api_key()
│   ├── function: check_port()
│   ├── function: start_server()
│   └── function: main()
├── test_all_commands_comprehensive.py
├── test_multi_turn_commands.py
├── test_real_world_scenarios.py
├── CHANGELOG.md
├── CHART_LOADING_SYSTEM_ANALYSIS.md
├── COMMAND_SYSTEM_TECHNICAL_SUMMARY.md
├── GITHUB_SUBMISSION.md
├── INSTALLATION_GUIDE.md
├── LICENSE
├── PHASE_5D_SUMMARY.md
├── PHASE_5E_1_FIX_SUMMARY.md
├── PHASE_5E_TEST_SUMMARY.md
├── PHASE_5E1_TEST_RESULTS.md
├── PHASE_5F_STRUCTURAL_AUDIT.md
├── PHASE_5F1_IMPLEMENTATION_SUMMARY.md
├── PHASE_5F1_PERFORMANCE_FIXES.md
├── PHASE_5F2_ARCHITECTURE_BREAKDOWN.md
├── PHASE_5F2_IMPLEMENTATION_SUMMARY.md
├── PHASE_5F2_TEST_LOGGING_SUMMARY.md
├── PROJECT_SUMMARY.md
├── QUICK_START.md
├── README.md
└── TRADE_COMMAND_SYSTEM_ANALYSIS.md
```

