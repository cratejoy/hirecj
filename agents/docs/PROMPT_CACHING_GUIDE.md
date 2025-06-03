# Anthropic Prompt Caching Guide for HireCJ

This guide explains how to enable and use Anthropic's prompt caching feature to reduce costs and latency when using Claude models.

## Overview

Anthropic's prompt caching allows you to cache frequently used context between API calls. This is particularly valuable for HireCJ where:
- CJ's identity and boundaries remain constant across conversations
- Merchant and scenario contexts are reused multiple times
- System prompts and tool definitions don't change

**Benefits:**
- **Cost Reduction**: Up to 90% reduction for cached content
- **Latency Reduction**: Up to 85% faster for long prompts
- **Better Performance**: Allows using more context without cost concerns

## Supported Models

Prompt caching is available for:
- Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`)
- Claude 3.5 Haiku (`claude-3-5-haiku-20241022`)
- Claude 3 Opus (`claude-3-opus-20240229`)
- Claude 3 Sonnet (`claude-3-sonnet-20240229`)
- Claude 3 Haiku (`claude-3-haiku-20240307`)

## How It Works

1. **Cache Control**: Add `cache_control: {"type": "ephemeral"}` to message content
2. **Minimum Length**: Content must be at least 1024 tokens (2048 for Haiku)
3. **Cache Duration**: 5 minutes, refreshed on each use
4. **Cache Key**: Based on exact content match

## Implementation

### 1. Environment Setup

Set your Anthropic API key and model choice:

```bash
export ANTHROPIC_API_KEY=your_api_key_here
export CJ_MODEL=claude-3-5-sonnet-20241022
export MERCHANT_MODEL=claude-3-5-sonnet-20241022
```

### 2. Enable Caching in Code

The caching is automatically enabled when using Anthropic models through LiteLLM. The key is to structure your prompts correctly.

#### Direct LiteLLM Usage

```python
import litellm

# Enable the beta header for prompt caching
response = litellm.completion(
    model="claude-3-5-sonnet-20241022",
    messages=[
        {
            "role": "system",
            "content": [{
                "type": "text",
                "text": "Your large system prompt here...",
                "cache_control": {"type": "ephemeral"}
            }]
        },
        {
            "role": "user",
            "content": "User message"
        }
    ],
    extra_headers={
        "anthropic-beta": "prompt-caching-2024-07-31"
    }
)
```

#### With CrewAI Agents

Use the provided `create_cj_agent_with_caching` function:

```python
from app.agents.cj_agent_with_caching import create_cj_agent_with_caching

agent = create_cj_agent_with_caching(
    name="CJ",
    merchant_name="TechStyle Fashion Group",
    scenario_name="Growth Stall",
    cj_version="v5.0.0"
)
```

### 3. Caching Strategy

#### What to Cache

1. **System Prompts** (Highest Priority)
   - CJ identity and boundaries
   - Static instructions
   - Tool definitions

2. **Context Data** (Medium Priority)
   - Merchant information
   - Scenario details
   - Business metrics

3. **Conversation History** (Lower Priority)
   - Previous messages in multi-turn conversations
   - Only cache if conversation is long

#### What NOT to Cache

- User inputs (they change every time)
- Dynamic data that changes frequently
- Short content (< 1024 tokens)

### 4. Cost Analysis

With prompt caching enabled:

| Token Type | Standard Price | Cached Price | Savings |
|------------|----------------|--------------|---------|
| Input (Claude 3.5 Sonnet) | $3.00/1M | $0.30/1M | 90% |
| Cache Write | $3.75/1M | - | - |
| Cache Read | $0.30/1M | - | 90% |

**Example Scenario:**
- System prompt: 2,000 tokens
- Merchant context: 1,500 tokens
- 10 conversations per merchant

Without caching: 35,000 tokens × $3.00 = $0.105
With caching: 3,500 tokens (first write) × $3.75 + 31,500 tokens × $0.30 = $0.0131 + $0.0095 = $0.0226

**Savings: 78.5%**

### 5. Monitoring Cache Usage

Check the response usage to verify caching:

```python
# In the response object:
{
    "usage": {
        "input_tokens": 100,  # New tokens
        "cache_creation_input_tokens": 2000,  # Tokens written to cache
        "cache_read_input_tokens": 1500,  # Tokens read from cache
        "output_tokens": 200
    }
}
```

### 6. Best Practices

1. **Structure Messages for Caching**
   - Put static content at the beginning
   - Keep dynamic content at the end
   - Group related content together

2. **Optimize Cache Hits**
   - Use exact same content for cached sections
   - Don't modify cached content between calls
   - Wait for first response before sending parallel requests

3. **Monitor Performance**
   - Track cache hit rates
   - Monitor cost savings
   - Adjust caching strategy based on usage patterns

## Troubleshooting

### Cache Not Working

1. **Check Token Count**: Ensure content is > 1024 tokens
2. **Verify Headers**: Confirm `anthropic-beta` header is set
3. **Check Model**: Ensure using a supported Claude model
4. **Inspect Usage**: Look for `cache_*` fields in response

### High Cache Misses

1. **Content Changes**: Even small changes invalidate cache
2. **TTL Expiry**: Cache expires after 5 minutes of inactivity
3. **Order Matters**: Content must be in exact same order

## Next Steps

1. Enable caching for production CJ agents
2. Monitor cost savings and performance improvements
3. Optimize prompt structure for maximum cache efficiency
4. Consider implementing conversation-level caching for multi-turn scenarios
