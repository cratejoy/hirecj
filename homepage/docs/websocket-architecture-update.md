# WebSocket Architecture Updates - Phase 6.X3

## Summary

This update completes the implementation of the simplified WebSocket architecture by removing client-side conversation ID management in favor of server-side session-based conversation handling.

## Changes Made

### 1. **Removed conversationId from ShopifyOAuthButton**
- **File**: `src/components/ShopifyOAuthButton.tsx`
- Removed `conversationId` prop from interface
- Updated OAuth initiation to not send `conversation_id` parameter
- Backend now uses session cookies to determine user context

### 2. **Updated MessageContent Component**
- **File**: `src/components/MessageContent.tsx`
- Removed `conversationId` prop from interface
- Updated ShopifyOAuthButton usage to not pass conversationId
- Removed debug logs referencing conversationId

### 3. **Removed Obsolete OAuthButton Component**
- **File**: `src/components/OAuthButton.tsx` (deleted)
- This component was replaced by ShopifyOAuthButton but wasn't removed
- Used old OAuth flow with conversation_id parameter

### 4. **Updated SlackChat Component**
- **File**: `src/pages/SlackChat.tsx`
- Removed `conversationId` from ChatConfig interface
- Removed placeholder conversationId from state
- Cleaned up OAuth URL parameter handling (no more conversation_id)
- Updated debug interface to not reference conversationId
- Removed uuid import (no longer needed)

### 5. **Updated ChatInterface Component**
- **File**: `src/components/ChatInterface.tsx`
- Removed `conversationId` prop from interface
- Temporarily disabled annotation functionality pending session-based API update
- Added TODO comments for future session-based API implementation

## Backend Architecture (Already Implemented)

The backend now handles conversation management automatically:

1. **Cookie-based Authentication**: WebSocket reads `hirecj_session` cookie
2. **Smart Conversation ID Generation**:
   - Authenticated users: Reuses existing or creates persistent conversation
   - Anonymous users: Creates temporary conversation
3. **No Client Input**: Backend determines conversation ID internally

## Future Work

1. **Update Annotation API**: Convert from `/api/v1/conversations/{id}/annotations` to session-based endpoints
2. **Remove Temporary Mocks**: Once backend API is updated, remove the temporary mock responses in ChatInterface
3. **Add Session Management UI**: Allow users to view/manage their conversation history

## Benefits

1. **Simplified Frontend**: No need to manage conversation IDs client-side
2. **Better Security**: Server controls conversation access based on authentication
3. **Persistent Conversations**: Authenticated users automatically continue previous conversations
4. **Cleaner URLs**: No more conversation_id parameters in URLs