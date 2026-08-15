# Tasks

## Phase 1: Intent Type Definition
- [ ] Define `IntentType` enum with 6 intent types
- [ ] Document each intent type with examples
- [ ] Create `IntentClassification` Pydantic model
- [ ] Add validation for confidence scores (0.0-1.0)

## Phase 2: Classification Prompt Design
- [ ] Write classification system prompt
- [ ] Include clear examples for each intent type
- [ ] Specify JSON output format
- [ ] Test prompt with sample queries
- [ ] Optimize for low token usage

## Phase 3: Classifier Implementation
- [ ] Implement `IntentClassifierImpl` class
- [ ] Add async LLM classification with timeout
- [ ] Implement rule-based fallback classifier
- [ ] Add batch classification support
- [ ] Handle parsing errors gracefully

## Phase 4: Integration Testing
- [ ] Test with 50+ sample queries per intent type
- [ ] Measure classification accuracy
- [ ] Verify timeout behavior (< 5s)
- [ ] Test fallback activation on low confidence
- [ ] Validate JSON parsing edge cases

## Phase 5: Performance Optimization
- [ ] Profile classification latency
- [ ] Optimize prompt for speed
- [ ] Test concurrent classifications
- [ ] Measure p95 latency target (< 500ms)
- [ ] Tune temperature for consistency

## Acceptance Criteria
- All 6 intent types implemented
- Classification accuracy > 85% on test set
- Latency < 500ms p95
- Fallback works on timeout/error
- Batch classification functional
- Test coverage > 90%

## Notes
- Use DeepSeek Chat for cost efficiency
- Keep classification prompt minimal
- Log all classifications for analysis
- Monitor confidence score distribution
