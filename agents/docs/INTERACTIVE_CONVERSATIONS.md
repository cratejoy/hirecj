# Interactive Conversation System

## 🎯 Quick Start

```bash
make play
```

This launches the interactive menu system where you can:
- 🎯 **Browse** all available personas, scenarios, and workflows with descriptions
- 🎲 **Randomize** combinations for unexpected conversations
- 📚 **Choose** from recommended conversation setups
- 🔄 **Repeat** your last conversation instantly
- 📜 **Review** conversation history

## 🎭 Available Merchant Personas

### Marcus Thompson - Grill Masters Club
- **Personality**: Direct, data-driven, impatient
- **Communication**: Terse, drops punctuation, numbers-focused
- **Stress Level**: HIGH 😰
- **Sample**: "whats our cac / need those numbers now"

### Sarah Chen - EcoBeauty Box
- **Personality**: Collaborative, thoughtful, values-driven
- **Communication**: Detail-oriented, asks probing questions
- **Stress Level**: MODERATE 😐
- **Sample**: "I'm wondering if we should explore why customers are churning..."

### Zoe Martinez - Manifest & Chill (NEW!)
- **Personality**: Social media native, scattered, overwhelmed
- **Communication**: Stream of consciousness, emoji-heavy, screenshots everything
- **Stress Level**: HIGH 😰 (but maintaining positive vibes ✨)
- **Sample**: "omggg CJ help 😭 / i have 73 DMs asking about shipping delays"

## 📊 Business Scenarios

1. **Growth Plateau** - Stuck at 1,200 subscribers, CAC rising
2. **February Meltdown** - Quality crisis, 15% churn spike 🔥
3. **Viral Growth Problems** - 71% growth in 6 weeks, operations drowning
4. **New Competitor Pressure** - $5M funded rival stealing customers
5. **Post-COVID Plateau** - Mature business, margins squeezed

## 🔄 Conversation Workflows

- **Daily Flash Report** - Morning metrics with insights
- **Crisis Management** - Rapid-fire emergency support
- **Ad-hoc Chat** - Organic conversation flow
- **Weekly Business Review** - Strategic analysis session

## 🚀 Menu Features

### 1. Quick Start Menu
Navigate through interactive menus to select:
- Merchant persona (with personality preview)
- Business scenario (with stress indicators)
- Conversation workflow (with recommendations)
- CJ version

### 2. Random Conversation 🎲
Let the system pick a random but sensible combination.

### 3. Recommended Combinations 📚
Pre-selected interesting combinations like:
- "Data-Driven Crisis" - Marcus during quality meltdown
- "Influencer Overwhelm" - Zoe handling viral growth
- "Values vs Reality" - Sarah balancing sustainability with growth

### 4. Conversation History 📜
- View your last 10 conversations
- Instantly re-run any previous setup
- Track what combinations you've tried

### 5. Express Mode ⚡
Jump straight in with defaults (Marcus + growth stall + chat)

## 💡 Usage Examples

### Interactive Mode (Recommended)
```bash
make play
```

### Direct Launch (Skip Menus)
```bash
# Specific combination
python scripts/conversation_launcher.py --direct \
  --merchant zoe_martinez \
  --scenario scaling_chaos \
  --workflow daily_briefing

# Or use the old command
make conversation-play MERCHANT=zoe_martinez SCENARIO=scaling_chaos
```

## 🎨 Why This Design?

1. **Discovery**: You don't need to memorize available options
2. **Context**: Each option shows descriptions and characteristics
3. **Smart Defaults**: Workflows are recommended based on scenarios
4. **Quick Actions**: One-key shortcuts for common tasks
5. **History**: Never lose a good conversation setup

## 🔧 Architecture

The system consists of:

1. **Conversation Catalog** (`app/conversation_catalog.py`)
   - Central registry of all options with rich metadata
   - Personality types, stress levels, communication styles
   - Scenario urgency and key challenges

2. **Interactive Launcher** (`scripts/conversation_launcher.py`)
   - Menu-driven interface with discovery features
   - Conversation history tracking
   - Random and recommended combinations

3. **Existing Play System** (`scripts/play_conversation_simple.py`)
   - Unchanged core conversation engine
   - Now discoverable through the launcher

## 🚦 Tips for Great Conversations

1. **Match Stress Levels**: High-stress scenarios work great with Marcus or Zoe
2. **Try Contrasts**: Sarah's thoughtful approach during crisis scenarios
3. **Use Workflows**: Daily briefings reveal data patterns, crisis mode shows rapid support
4. **Embrace Chaos**: Zoe + viral growth + daily briefing = authentic founder overwhelm
5. **Save Favorites**: The history feature remembers your best combinations

Enjoy exploring the many personalities and situations in the HireCJ universe! 🎭
