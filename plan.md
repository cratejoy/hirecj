# HireCJ LLMDataAgent: Accumulating Universe Facts Implementation Plan

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Every decision should make the code simpler, not more complex
2. **No Cruft**: Remove all redundant code, validation, and unnecessary complexity
3. **Break It & Fix It Right**: No backwards compatibility shims - make breaking changes and migrate properly
4. **Long-term Elegance**: Choose performant, compiler-enforced solutions that prevent subtle bugs
5. **Backend-Driven**: Let the backend handle complexity, frontend should be a thin client
6. **Single Source of Truth**: One pattern, one way to do things, no alternatives
7. **No Over-Engineering**: Design for current needs only - no hypothetical features

## 🏗️ Architecture: Accumulating Universe Facts

The LLMDataAgent maintains conversation consistency by accumulating facts across tool calls:

```
┌─────────────────────────────────────────────────────────────┐
│                        API Request                           │
│                     (with session_id)                        │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLMDataAgent                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Universe Facts (Redis)                   │   │
│  │  • entities: {id → properties}                       │   │
│  │  • metrics: {name → value}                          │   │
│  │  • relationships: {entity → [related]}              │   │
│  │  • invariants: [rules]                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                               │                              │
│                               ▼                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Enhanced LLM Generation                     │   │
│  │  1. Include facts in prompt                         │   │
│  │  2. Generate consistent response                    │   │
│  │  3. Extract new facts                              │   │
│  │  4. Update universe facts                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📅 Phased Implementation Checklist

### Phase 1: Foundation
- [ ] Create feature branch `feature/llm-data-agent-universe-facts`
- [ ] Add `universe_facts` dict structure to LLMDataAgent
- [ ] Implement `_load_or_initialize_facts()` with Redis integration
- [ ] Add `session_id` parameter through the call stack
- [ ] Create basic fact categories (entities, metrics, relationships, invariants)
- [ ] Write unit tests for fact initialization and storage

### Phase 2: Core Generation
- [ ] Implement `_build_facts_context()` method
- [ ] Modify `_generate_response()` to include facts in prompts
- [ ] Add consistency instructions to system prompt
- [ ] Implement `_save_facts()` to persist to Redis
- [ ] Add session TTL configuration
- [ ] Write integration tests for fact persistence

### Phase 3: Fact Extraction
- [ ] Implement `_extract_entities_from_dict()` for ID extraction
- [ ] Implement `_extract_metrics()` for numeric values
- [ ] Implement `_extract_relationships()` for entity connections
- [ ] Create `_infer_entity_type()` helper
- [ ] Add fact extraction to all response types
- [ ] Write tests for extraction accuracy

### Phase 4: Method Updates
- [ ] Update `get_support_dashboard()` to store metrics
- [ ] Update `search_tickets()` to respect metrics and store entities
- [ ] Update `get_ticket()` to use existing entities
- [ ] Update `get_customer()` to maintain relationships
- [ ] Update historical methods to align with current state
- [ ] Write consistency tests for each method

### Phase 5: Validation & Refinement
- [ ] Implement invariant generation from patterns
- [ ] Add response validation against invariants
- [ ] Implement retry logic for inconsistent responses
- [ ] Add metrics/logging for fact accumulation
- [ ] Performance optimization (batch Redis operations)
- [ ] Load testing with multiple concurrent sessions

### Phase 6: Integration & Deployment
- [ ] Update API layer to pass session_id
- [ ] Add feature flag for gradual rollout
- [ ] Document the new consistency model
- [ ] Create monitoring dashboard for Redis usage
- [ ] Deploy to staging environment
- [ ] Run comprehensive integration tests

### Phase 7: Production Rollout
- [ ] Monitor staging performance and consistency
- [ ] Fix any edge cases discovered
- [ ] Gradual production rollout (10% → 50% → 100%)
- [ ] Monitor production metrics
- [ ] Gather feedback and iterate

## 🎯 The Core Problem

The LLMDataAgent currently has **zero memory** between tool calls within a conversation:
- Says "40 open tickets" in dashboard
- User asks about shipping delays
- Generates completely different universe with 10 tickets
- No consistency, no coherent story

## 💡 The Elegant Solution: Accumulating Universe Facts

Instead of pre-generating everything (doesn't scale to months/years) or having no memory (current broken state), we maintain a **growing set of established facts** that each new generation must respect.

```python
# Core concept:
universe_facts = {
    "entities": {"ticket_1234": {"status": "open", "category": "shipping"}},
    "metrics": {"total_tickets": 40, "shipping_percentage": 0.15},
    "relationships": {"cust_5678": ["ticket_1234", "ticket_5555"]},
    "invariants": ["ticket counts must sum to total_tickets"]
}

# Every LLM call includes these facts and must respect them
```

## ✅ Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Add `universe_facts` dict to LLMDataAgent.__init__
- [ ] Create fact extraction methods (`_extract_facts_from_response`)
- [ ] Modify `_generate_response` to include facts in prompt
- [ ] Add session_id parameter to track facts per conversation
- [ ] Create fact categories: entities, metrics, relationships, invariants

### Phase 2: Fact Extraction 
- [ ] Extract entities (IDs, key properties) from responses
- [ ] Extract metrics (counts, percentages, totals) from responses
- [ ] Extract relationships (customer->tickets, etc.) from responses
- [ ] Build invariant rules from established patterns

### Phase 3: Consistency Enforcement
- [ ] Include facts in every LLM prompt
- [ ] Add consistency instructions to system prompt
- [ ] Validate responses against invariants
- [ ] Add retry logic for inconsistent responses

### Phase 4: Session Management
- [ ] Pass session_id through from API layer
- [ ] Store facts in Redis with session key
- [ ] Set TTL on session facts (e.g., 24 hours)
- [ ] Clean up expired sessions

### Phase 5: Testing & Validation
- [ ] Test fact accumulation across multiple calls
- [ ] Test consistency maintenance
- [ ] Test historical data generation respects current state
- [ ] Test edge cases (conflicting facts, retries)

## 📋 Detailed Implementation

### 1. Core Data Structure

```python
class LLMDataAgent:
    def __init__(self, merchant_name: str, scenario_name: str, model_config: ModelConfig, 
                 session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.universe_facts = self._load_or_initialize_facts()
        
    def _load_or_initialize_facts(self) -> Dict[str, Any]:
        """Load existing facts from Redis or initialize new"""
        if cached := redis_client.get(f"facts:{self.session_id}"):
            return json.loads(cached)
        
        return {
            "entities": {},      # id -> {properties}
            "metrics": {},       # metric_name -> value
            "relationships": {}, # entity_id -> [related_ids]
            "invariants": [],    # rules that must hold
            "generated_at": []   # timestamp -> what was generated
        }
```

### 2. Enhanced Generation Method

```python
def _generate_response(self, prompt: str, response_format: Dict[str, Any]) -> Any:
    """Generate response with universe facts context"""
    
    # Build consistency context
    facts_context = self._build_facts_context()
    
    enhanced_prompt = f"""
{prompt}

IMPORTANT: You must maintain consistency with the established universe facts:

{facts_context}

Your response MUST:
1. Use existing entity IDs when referring to known entities
2. Respect all stated metrics and counts
3. Maintain relationships between entities
4. Follow all invariant rules
5. Generate new data that fits logically with established facts
"""
    
    response = self._call_llm(enhanced_prompt, response_format)
    
    # Extract and store new facts
    self._extract_and_store_facts(response)
    
    return response
```

### 3. Fact Extraction

```python
def _extract_and_store_facts(self, response: Any) -> None:
    """Extract facts from LLM response and update universe facts"""
    
    # Extract entities (anything with an ID)
    if isinstance(response, dict):
        self._extract_entities_from_dict(response)
    elif isinstance(response, list):
        for item in response:
            self._extract_entities_from_dict(item)
    
    # Extract metrics
    self._extract_metrics(response)
    
    # Extract relationships
    self._extract_relationships(response)
    
    # Generate invariants
    self._update_invariants()
    
    # Save to Redis
    self._save_facts()

def _extract_entities_from_dict(self, data: Dict[str, Any]) -> None:
    """Extract entities with IDs and key properties"""
    if "id" in data or "ticket_id" in data or "customer_id" in data:
        entity_id = data.get("id") or data.get("ticket_id") or data.get("customer_id")
        
        # Store key properties that should remain consistent
        self.universe_facts["entities"][entity_id] = {
            "type": self._infer_entity_type(entity_id),
            "properties": {
                k: v for k, v in data.items() 
                if k in ["status", "category", "priority", "name", "email"]
            }
        }
```

### 4. Fact Context Building

```python
def _build_facts_context(self) -> str:
    """Build human-readable context from universe facts"""
    
    context_parts = []
    
    # Entities
    if self.universe_facts["entities"]:
        context_parts.append("Known Entities:")
        for entity_id, props in self.universe_facts["entities"].items():
            context_parts.append(f"  - {entity_id}: {props}")
    
    # Metrics
    if self.universe_facts["metrics"]:
        context_parts.append("\nEstablished Metrics:")
        for metric, value in self.universe_facts["metrics"].items():
            context_parts.append(f"  - {metric}: {value}")
    
    # Relationships
    if self.universe_facts["relationships"]:
        context_parts.append("\nRelationships:")
        for entity, related in self.universe_facts["relationships"].items():
            context_parts.append(f"  - {entity} -> {related}")
    
    # Invariants
    if self.universe_facts["invariants"]:
        context_parts.append("\nRules to Follow:")
        for rule in self.universe_facts["invariants"]:
            context_parts.append(f"  - {rule}")
    
    return "\n".join(context_parts)
```

### 5. Specific Method Updates

```python
def get_support_dashboard(self, current_day: Optional[int] = None) -> SupportDashboard:
    """Generate dashboard that respects established metrics"""
    
    # If we already have total_tickets metric, include it
    existing_metrics = self.universe_facts.get("metrics", {})
    
    prompt = f"""Generate a support dashboard for {self.merchant_name}..."""
    
    response = self._generate_response(prompt, response_format)
    
    # Extract metrics for future consistency
    self.universe_facts["metrics"].update({
        "total_tickets": response.get("total_tickets"),
        "open_tickets": response.get("open_tickets"),
        "response_time_hours": response.get("avg_response_time_hours"),
    })
    
    return SupportDashboard(**response)

def search_tickets(self, query: str, category: Optional[str] = None) -> List[Ticket]:
    """Search tickets ensuring consistency with dashboard metrics"""
    
    # Include known ticket counts to ensure consistency
    total_tickets = self.universe_facts["metrics"].get("total_tickets", "unknown")
    category_percentages = self._get_category_percentages()
    
    prompt = f"""Search for tickets matching '{query}'...
    
    Note: The system currently has {total_tickets} total tickets.
    {category_percentages}
    """
    
    response = self._generate_response(prompt, response_format)
    
    # Store ticket entities for future reference
    for ticket in response:
        self.universe_facts["entities"][ticket["id"]] = {
            "type": "ticket",
            "properties": {
                "status": ticket.get("status"),
                "category": ticket.get("category"),
                "customer_id": ticket.get("customer_id")
            }
        }
    
    return [Ticket(**t) for t in response]
```

### 6. Testing Strategy

```python
def test_consistency_across_calls():
    """Test that facts accumulate and maintain consistency"""
    
    agent = LLMDataAgent("test_merchant", "test_scenario", session_id="test_123")
    
    # First call: dashboard
    dashboard = agent.get_support_dashboard()
    assert dashboard.total_tickets == 40  # example
    
    # Second call: search should respect total
    tickets = agent.search_tickets("shipping")
    
    # Verify consistency
    facts = agent.universe_facts
    assert facts["metrics"]["total_tickets"] == 40
    assert len([t for t in tickets if t.category == "shipping"]) > 0
    
    # Third call: specific ticket should exist
    ticket_id = tickets[0].id
    ticket_detail = agent.get_ticket(ticket_id)
    assert ticket_detail.id == ticket_id
    
    # Historical data should lead to current state
    historical = agent.get_historical_metrics(days=30)
    assert historical[-1]["total_tickets"] == 40  # current day matches
```

## 🚀 Migration Path

1. **Update LLMDataAgent class** with universe_facts
2. **Add session_id parameter** through the stack (API -> CJAgent -> LLMDataAgent)
3. **Deploy with feature flag** to test consistency
4. **Monitor Redis memory usage** for fact storage
5. **Add metrics** for fact accumulation and consistency violations

## 📊 Success Metrics

- Zero consistency violations in conversations
- Facts accumulate properly across tool calls
- Historical data aligns with current state
- Memory usage remains reasonable (< 1MB per session)
- No performance degradation (< 100ms overhead)

## 🔮 Future Extensions (NOT NOW)

- Fact compression for long conversations
- Cross-session fact sharing for merchant continuity
- Fact conflicts resolution strategies
- ML-based invariant discovery

Remember: Build for today's needs, not tomorrow's possibilities!