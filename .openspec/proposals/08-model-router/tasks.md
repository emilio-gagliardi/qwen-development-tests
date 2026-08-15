# Tasks

## Phase 1: Routing Configuration
- [ ] Define `ModelTier` enum with FAST, BALANCED, ADVANCED
- [ ] Create `ROUTING_CONFIG` dictionary for all 6 intent types
- [ ] Add cost per million tokens for all models
- [ ] Document routing logic decisions

## Phase 2: Router Implementation
- [ ] Implement `ModelRouterImpl` class
- [ ] Add confidence-based tier selection logic
- [ ] Implement model selection from tier
- [ ] Add reasoning generation
- [ ] Implement cost estimation

## Phase 3: Routing Explanations
- [ ] Implement `get_routing_explanation()` method
- [ ] Generate human-readable explanations
- [ ] Document all routing paths
- [ ] Add examples to documentation

## Phase 4: Testing & Validation
- [ ] Test all intent type routing paths
- [ ] Verify confidence threshold behavior
- [ ] Validate cost calculations
- [ ] Measure routing latency (< 50ms target)
- [ ] Test error handling

## Phase 5: Cost Analysis
- [ ] Calculate expected cost savings vs single-tier
- [ ] Create cost comparison dashboard
- [ ] Monitor actual costs in Langfuse
- [ ] Optimize routing config based on data

## Acceptance Criteria
- All 6 intent types have routing rules
- Confidence thresholds work correctly
- Cost estimates accurate within 10%
- Routing latency < 50ms p99
- Clear explanations generated
- Test coverage > 90%

## Notes
- Start conservative (favor cheaper tiers)
- Adjust thresholds based on quality feedback
- Monitor cost/quality tradeoffs
- Document all configuration changes
