import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ShopifyOAuthButton } from './ShopifyOAuthButton';

interface UIElement {
  id: string;
  type: string;
  provider: string;
  placeholder: string;
}

interface MessageContentProps {
  content: string;
  conversationId: string;
  isThinking?: boolean;
  ui_elements?: UIElement[];
}

export const MessageContent: React.FC<MessageContentProps> = ({
  content,
  conversationId,
  isThinking = false,
  ui_elements = []
}) => {
  // Pattern matching fallback for OAuth prompts
  const shopifyPromptPatterns = [
    /connect.*shopify/i,
    /shopify.*connect/i,
    /link.*shopify/i,
    /shopify.*account/i,
    /ready.*connect.*store/i,
    /let's get.*shopify/i,
    /click.*button.*shopify/i
  ];

  const shouldShowShopifyButton = shopifyPromptPatterns.some(pattern => 
    pattern.test(content)
  );

  // If no UI elements but pattern matches, show button after content
  if ((!ui_elements || ui_elements.length === 0) && shouldShowShopifyButton && !isThinking) {
    return (
      <div>
        <div className="text-sm prose prose-sm max-w-none prose-invert">
          <ReactMarkdown 
            components={{
              // Customize paragraph styling to match existing
              p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
              // Style other elements to match the chat theme
              strong: ({children}) => <strong className="font-semibold">{children}</strong>,
              em: ({children}) => <em className="italic">{children}</em>,
              code: ({children}) => <code className="bg-gray-600 px-1 py-0.5 rounded text-xs">{children}</code>,
              ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
              ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
              li: ({children}) => <li className="text-sm">{children}</li>,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
        <div className="mt-4">
          <ShopifyOAuthButton conversationId={conversationId} />
        </div>
      </div>
    );
  }

  // If no UI elements and no pattern match, render content directly
  if (!ui_elements || ui_elements.length === 0) {
    return (
      <div className="text-sm prose prose-sm max-w-none prose-invert">
        <ReactMarkdown 
          components={{
            // Customize paragraph styling to match existing
            p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
            // Style other elements to match the chat theme
            strong: ({children}) => <strong className="font-semibold">{children}</strong>,
            em: ({children}) => <em className="italic">{children}</em>,
            code: ({children}) => <code className="bg-gray-600 px-1 py-0.5 rounded text-xs">{children}</code>,
            ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
            ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
            li: ({children}) => <li className="text-sm">{children}</li>,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  }

  // Split content by placeholders and render with UI elements
  const placeholderRegex = /__OAUTH_BUTTON_\d+__/g;
  const parts = content.split(placeholderRegex);
  const placeholders = content.match(placeholderRegex) || [];
  
  // Map placeholders to their corresponding UI elements
  const elementMap = new Map<string, UIElement>();
  ui_elements.forEach(elem => {
    elementMap.set(elem.placeholder, elem);
  });
  
  // Debug log UI elements if they contain OAuth buttons
  if (ui_elements.some(elem => elem.type === 'oauth_button')) {
    console.log('🛍️ MessageContent - OAuth button detected');
    console.log('  UI Elements:', ui_elements);
    console.log('  Conversation ID:', conversationId);
  }

  return (
    <div className="space-y-3">
      {parts.map((part, index) => (
        <React.Fragment key={index}>
          {part && (
            <div className="text-sm prose prose-sm max-w-none prose-invert">
              <ReactMarkdown
                components={{
                  // Customize paragraph styling to match existing
                  p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                  // Style other elements to match the chat theme
                  strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                  em: ({children}) => <em className="italic">{children}</em>,
                  code: ({children}) => <code className="bg-gray-600 px-1 py-0.5 rounded text-xs">{children}</code>,
                  ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                  ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                  li: ({children}) => <li className="text-sm">{children}</li>,
                }}
              >
                {part.trim()}
              </ReactMarkdown>
            </div>
          )}
          {index < placeholders.length && placeholders[index] && (
            <div className="my-4">
              {elementMap.get(placeholders[index])?.type === 'oauth_button' && (
                <ShopifyOAuthButton 
                  conversationId={conversationId}
                />
              )}
            </div>
          )}
        </React.Fragment>
      ))}
    </div>
  );
};