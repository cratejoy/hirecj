# 🚀 HireCJ Chat Integration Master Plan

---

## 📊 Current Status

| Component | Status | Progress |
|-----------|--------|----------|
| **Backend API** | ✅ Complete | Ready at `localhost:8000` |
| **Phase 1: Configuration** | 🔴 Not Started | 0% |
| **Phase 2: WebSocket Chat** | 🔴 Not Started | 0% |
| **Phase 3: Annotations** | 🔴 Not Started | 0% |
| **Phase 4: Fact Checking** | 🔴 Not Started | 0% |
| **Phase 5: Polish** | 🔴 Not Started | 0% |

### 🎯 Next Steps
1. **Set up development environment** - Run both backend and frontend
2. **Create ConfigurationModal component** - Start Phase 1
3. **Test API connectivity** - Verify catalog endpoints work

---

## 🎨 Overview

Transform the "Chat with CJ" button into a fully interactive experience where users:
1. Select a merchant persona (e.g., Marcus Thompson)
2. Choose a business scenario (e.g., steady operations)
3. Have real-time conversations with CJ
4. Annotate responses with feedback
5. Fact-check CJ's claims against universe data

**Tech Stack**: React + TypeScript + WebSocket + FastAPI

---

## 📋 Phase 1: Configuration Selection
**Duration**: 2-3 days | **Status**: 🔴 Not Started

### Goals
- Let users select merchant/scenario combination
- Fetch available options from API
- Validate universe exists before starting chat

### Tasks
- [ ] Create `ConfigurationModal.tsx` component
- [ ] Add merchant selection cards with personality traits
- [ ] Add scenario selection with descriptions
- [ ] Integrate catalog API endpoints
- [ ] Add loading states and error handling
- [ ] Create "Start Chat" transition

### API Endpoints
```typescript
GET /api/v1/catalog/merchants     // List all merchants
GET /api/v1/catalog/scenarios     // List all scenarios  
GET /api/v1/catalog/universes     // Check valid combinations
```

### Components
```typescript
// ConfigurationModal.tsx
interface ConfigState {
  merchant: string | null;
  scenario: string | null;
  universe: Universe | null;
}

// MerchantCard.tsx
- Name, business, personality
- Communication style preview
- Sample message

// ScenarioCard.tsx  
- Scenario name & description
- Stress level indicator
- Key metrics preview
```

### Success Criteria
- [ ] User can see all available merchants
- [ ] User can see scenarios for selected merchant
- [ ] Only valid combinations are selectable
- [ ] Clear CTA to start conversation

---

## 📡 Phase 2: WebSocket Chat Implementation
**Duration**: 3-4 days | **Status**: 🔴 Not Started

### Goals
- Establish WebSocket connection
- Handle real-time message flow
- Show CJ thinking/progress states
- Auto-save conversations

### Tasks
- [ ] Create `useWebSocketChat` hook
- [ ] Update `ChatInterface.tsx` for real messages
- [ ] Add progress indicator component
- [ ] Handle connection lifecycle
- [ ] Implement message queue
- [ ] Add reconnection logic

### WebSocket Protocol
```javascript
// Connection
ws://localhost:8000/ws/chat/{conversationId}

// Send message
{
  "type": "message",
  "text": "Hello CJ!",
  "merchant_id": "marcus_thompson",
  "scenario": "steady_operations"
}

// Receive updates
- system: Connection status
- cj_thinking: Progress updates
- cj_message: Actual response
- error: Error messages
```

### Progress States
```typescript
interface Progress {
  status: 'initializing' | 'creating agent' | 'generating response' | 'using tool';
  toolsCalled?: number;
  currentTool?: string;
  elapsed?: number;
}
```

### Components
```typescript
// ChatInterface.tsx
- Message list with auto-scroll
- Input field with send button
- Connection status indicator

// ProgressIndicator.tsx
- "CJ is thinking..." animation
- Tool usage display
- Elapsed time counter

// MessageBubble.tsx
- Sender avatar (CJ/User)
- Message content
- Timestamp
- Action buttons placeholder
```

### Success Criteria
- [ ] Messages send/receive in real-time
- [ ] Progress updates show during CJ response
- [ ] Connection errors handled gracefully
- [ ] Conversations auto-save on close
- [ ] Smooth scrolling and animations

---

## 👍 Phase 3: Annotation System
**Duration**: 2 days | **Status**: 🔴 Not Started

### Goals
- Add like/dislike buttons to messages
- Allow optional text feedback
- Persist annotations with conversation
- Show annotation state visually

### Tasks
- [ ] Add annotation buttons to MessageBubble
- [ ] Create annotation modal for text input
- [ ] Integrate annotation API
- [ ] Add visual feedback for annotated messages
- [ ] Handle annotation updates/deletes

### API Integration
```typescript
// Add annotation
POST /api/v1/conversations/{id}/annotations/{messageIndex}
{
  "sentiment": "like" | "dislike",
  "text": "Optional feedback"
}

// Remove annotation  
DELETE /api/v1/conversations/{id}/annotations/{messageIndex}
```

### Components
```typescript
// AnnotationButtons.tsx
- Thumbs up/down icons
- Hover state animations
- Selected state styling

// AnnotationModal.tsx
- Text input for feedback
- Sentiment toggle
- Save/Cancel buttons

// AnnotationIndicator.tsx
- Small badge on annotated messages
- Tooltip with annotation text
```

### UI/UX Flow
1. Hover message → Show annotation buttons
2. Click thumb → Toggle sentiment
3. Click again → Open text modal
4. Visual feedback → Badge + highlight

### Success Criteria
- [ ] All CJ messages have annotation buttons
- [ ] Annotations persist across sessions
- [ ] Clear visual feedback
- [ ] Smooth interactions

---

## ✅ Phase 4: Fact-Checking Integration  
**Duration**: 3 days | **Status**: 🔴 Not Started

### Goals
- Add fact-check button to CJ messages
- Show real-time checking progress
- Display detailed results
- Handle async updates elegantly

### Tasks
- [ ] Add fact-check button to messages
- [ ] Create fact-check results modal
- [ ] Implement status polling/WebSocket updates
- [ ] Design claim visualization
- [ ] Add caching for checked messages

### API Flow
```typescript
// Start fact-check
POST /api/v1/conversations/{id}/fact-checks/{messageIndex}

// Check status (polling or WebSocket)
GET /api/v1/conversations/{id}/fact-checks/{messageIndex}

// Response states
- status: "checking" → Show progress
- status: "complete" → Show results
```

### Components
```typescript
// FactCheckButton.tsx
- Icon button with tooltip
- Loading spinner when checking
- Result indicator when complete

// FactCheckModal.tsx
- Overall status (PASS/WARNING/FAIL)
- Individual claims list
- Verification details
- Execution time

// ClaimCard.tsx
- Claim text
- Status (VERIFIED/INCORRECT/UNVERIFIABLE)
- Actual data vs claimed
- Source reference
```

### Visual Design
```
✅ VERIFIED - Green background
❌ INCORRECT - Red background  
⚠️ WARNING - Yellow background
🔄 CHECKING - Animated spinner
```

### Success Criteria
- [ ] Fact-check available for all CJ messages
- [ ] Real-time progress updates
- [ ] Clear, scannable results
- [ ] Results cached to avoid re-checking

---

## ✨ Phase 5: Polish & Launch
**Duration**: 2-3 days | **Status**: 🔴 Not Started

### Goals
- Smooth user experience
- Error handling
- Performance optimization
- Mobile responsiveness
- Documentation

### Tasks
- [ ] Add smooth transitions between states
- [ ] Implement error boundaries
- [ ] Add loading skeletons
- [ ] Optimize WebSocket message batching
- [ ] Test on mobile devices
- [ ] Write user documentation

### Error States
```typescript
// Universe not found
"This combination isn't available yet. Try:"
→ Show available options

// Connection lost
"Connection interrupted. Reconnecting..."
→ Auto-retry with backoff

// API errors
"Something went wrong. Please try again."
→ Offer retry or report issue
```

### Performance
- Lazy load fact-check results
- Virtual scroll for long conversations
- Debounce annotation updates
- Message batching for WebSocket

### Mobile Considerations
- Full-screen chat on mobile
- Touch-friendly annotation buttons
- Swipe gestures for actions
- Responsive modals

### Success Criteria
- [ ] < 100ms UI response time
- [ ] Graceful error recovery
- [ ] Works on all screen sizes
- [ ] Intuitive without instructions

---

## 🛠️ Technical Architecture

### Frontend Structure
```
client/src/
├── components/
│   ├── chat/
│   │   ├── ChatInterface.tsx
│   │   ├── ConfigurationModal.tsx
│   │   ├── MessageBubble.tsx
│   │   └── ProgressIndicator.tsx
│   ├── annotations/
│   │   ├── AnnotationButtons.tsx
│   │   └── AnnotationModal.tsx
│   └── fact-checking/
│       ├── FactCheckButton.tsx
│       ├── FactCheckModal.tsx
│       └── ClaimCard.tsx
├── hooks/
│   ├── useWebSocketChat.ts
│   ├── useAnnotations.ts
│   └── useFactCheck.ts
├── services/
│   ├── api.ts
│   └── websocket.ts
└── types/
    └── chat.types.ts
```

### State Management
```typescript
// Simple context for POC
interface ChatContext {
  // Configuration
  merchant: Merchant | null;
  scenario: Scenario | null;
  conversationId: string;
  
  // Chat state
  messages: Message[];
  isConnected: boolean;
  progress: Progress | null;
  
  // Features
  annotations: Record<number, Annotation>;
  factChecks: Record<number, FactCheckResult>;
}
```

### Environment Setup
```bash
# Frontend .env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000

# Development
cd ../hirecj-agents && python src/api/server.py  # Backend on :8000
cd ../hirecj-homepage && npm run dev           # Frontend on :3456
```

---

## 📅 Timeline

### Week 1 (Days 1-5)
- **Mon-Tue**: Phase 1 - Configuration
- **Wed-Fri**: Phase 2 - WebSocket Chat (start)

### Week 2 (Days 6-10)  
- **Mon**: Phase 2 - WebSocket Chat (complete)
- **Tue-Wed**: Phase 3 - Annotations
- **Thu-Fri**: Phase 4 - Fact Checking

### Week 3 (Days 11-12)
- **Mon-Tue**: Phase 5 - Polish & Launch

---

## 🎯 Definition of Done

### MVP Launch Criteria
- [ ] Users can select any valid merchant/scenario combo
- [ ] Real-time chat works reliably
- [ ] Messages can be annotated
- [ ] Fact-checking shows accurate results
- [ ] No critical bugs
- [ ] Works on desktop and mobile
- [ ] Error states handled gracefully

### Demo-Ready Checklist
- [ ] 2-3 minute happy path works perfectly
- [ ] Visual polish matches brand
- [ ] Performance feels instant
- [ ] Errors don't break the experience

---

## 📝 Notes

This is a **proof of concept** optimized for:
- **Simplicity** over scalability
- **Speed** of implementation
- **Demo-ability** over production readiness

Future enhancements (not in scope):
- Authentication
- Multi-user support
- Conversation history browser
- Advanced analytics
- Workflow selection