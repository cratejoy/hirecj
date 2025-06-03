import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ShopifyOAuthButton } from './ShopifyOAuthButton';

interface MessageContentProps {
  content: string;
  conversationId: string;
  isThinking?: boolean;
}

export const MessageContent: React.FC<MessageContentProps> = ({
  content,
  conversationId,
  isThinking = false
}) => {
  // Check if the message contains OAuth prompts
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
      
      {shouldShowShopifyButton && !isThinking && (
        <div className="mt-4">
          <ShopifyOAuthButton conversationId={conversationId} />
        </div>
      )}
    </div>
  );
};