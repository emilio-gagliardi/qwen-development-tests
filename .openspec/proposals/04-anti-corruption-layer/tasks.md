# Tasks

## Phase 1: Protocol Definitions
- [ ] Define `LLMGateway` protocol with all required methods
- [ ] Define `IntentClassifier` protocol
- [ ] Define `ModelRouter` protocol
- [ ] Define `DocumentStore` protocol
- [ ] Define `TelemetryClient` protocol
- [ ] Document protocol contracts and error conditions

## Phase 2: Registry Implementation
- [ ] Implement `ServiceRegistry` class
- [ ] Add support for direct registration
- [ ] Add support for lazy factory registration
- [ ] Implement proper error handling with ConfigurationError
- [ ] Add clear() method for testing
- [ ] Write unit tests for registry operations

## Phase 3: Adapter Implementations
- [ ] Create `LiteLLMGatewayAdapter` implementing LLMGateway
- [ ] Create `HaystackDocumentStoreAdapter` implementing DocumentStore
- [ ] Create `LangfuseTelemetryAdapter` implementing TelemetryClient
- [ ] Create `IntentClassifierImpl` implementing IntentClassifier
- [ ] Create `ModelRouterImpl` implementing ModelRouter
- [ ] Test adapters with mock external services

## Phase 4: Integration
- [ ] Bootstrap service registration at application startup
- [ ] Wire up lazy initialization factories
- [ ] Test dependency injection flow
- [ ] Verify no direct imports in domain/application layers
- [ ] Document adapter usage patterns

## Phase 5: Testing & Validation
- [ ] Write unit tests with protocol mocks
- [ ] Test adapter error handling
- [ ] Verify lazy initialization works correctly
- [ ] Test registry thread safety
- [ ] Validate protocol compliance with mypy
- [ ] Achieve >90% test coverage

## Acceptance Criteria
- All 5 protocols defined and documented
- ServiceRegistry supports both eager and lazy registration
- All adapters implement their respective protocols
- Zero direct external library imports in domain layer
- Easy mocking for unit tests demonstrated
- Test coverage >90% for ACL module

## Notes
- Keep protocols focused on domain needs, not external API details
- Adapters should handle all translation logic
- Document protocol contracts clearly for team reference
- Use typing.Protocol for runtime compatibility
