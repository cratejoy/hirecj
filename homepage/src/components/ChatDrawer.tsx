import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  id: string;
  sender: 'user' | 'cj';
  content: string;
  timestamp: string;
}

interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  messages: Message[];
  isTyping: boolean;
  onSendMessage: (message: string) => void;
  onOptionClick: (option: number) => void;
}

const ChatDrawer: React.FC<ChatDrawerProps> = ({ 
  isOpen, 
  onClose, 
  messages, 
  isTyping,
  onSendMessage,
  onOptionClick
}) => {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Focus input when drawer opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 300);
    }
  }, [isOpen]);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);
  
  const handleSendMessage = () => {
    if (inputValue.trim()) {
      console.log('[UI] User submitting message (ChatDrawer):', inputValue.trim());
      onSendMessage(inputValue);
      setInputValue('');
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    } else if (e.key === 'Escape') {
      onClose();
    }
  };
  
  return (
    <>
      {/* Overlay */}
      <div 
        className={`fixed inset-0 bg-black z-40 overlay ${isOpen ? 'open' : ''}`}
        onClick={onClose}
      ></div>
      
      {/* Drawer */}
      <div className={`chat-drawer fixed bottom-0 inset-x-0 bg-chat-bg text-white z-50 h-[85vh] rounded-t-xl shadow-2xl ${isOpen ? 'open' : ''}`}>
        {/* Chat Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center">
            <div className="flex items-center mr-4">
              <span className="font-medium">Slack</span>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 ml-1" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="flex items-center text-gray-300">
              <span>#making-money</span>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="text-gray-400 hover:text-white p-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        {/* Chat Messages */}
        <div className="h-[calc(85vh-160px)] overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div key={message.id} className="flex items-start">
              {message.sender === 'cj' ? (
                <>
                  <div className="flex-shrink-0 mr-3">
                    <div className="bg-cratejoy-teal w-10 h-10 rounded flex items-center justify-center text-white">
                      <span className="font-semibold">CJ</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center">
                      <span className="font-medium">CJ</span>
                      <span className="text-gray-400 text-xs ml-2">{message.timestamp}</span>
                    </div>
                    <div className="mt-1 font-mono max-w-[90%]">
                      <p dangerouslySetInnerHTML={{ __html: message.content.replace(/\n/g, '<br />') }}></p>
                      
                      {/* Show option buttons for the first message */}
                      {message.id === '1' && (
                        <div className="mt-3 space-y-2">
                          <button 
                            onClick={() => onOptionClick(1)}
                            className="w-full text-left bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded transition duration-200"
                          >
                            [1] Slash 70% of support tickets
                          </button>
                          <button 
                            onClick={() => onOptionClick(2)}
                            className="w-full text-left bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded transition duration-200"
                          >
                            [2] Rescue bad reviews & boost NPS
                          </button>
                          <button 
                            onClick={() => onOptionClick(3)}
                            className="w-full text-left bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded transition duration-200"
                          >
                            [3] Make product pages convert higher
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex-shrink-0 mr-3">
                    <div className="bg-linkedin-blue w-10 h-10 rounded flex items-center justify-center text-white">
                      <span className="font-semibold">You</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center">
                      <span className="font-medium">You</span>
                      <span className="text-gray-400 text-xs ml-2">{message.timestamp}</span>
                    </div>
                    <div className="mt-1 font-mono">
                      <p>{message.content}</p>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))}
          
          {/* Typing indicator */}
          {isTyping && (
            <div className="flex items-start">
              <div className="flex-shrink-0 mr-3">
                <div className="bg-cratejoy-teal w-10 h-10 rounded flex items-center justify-center text-white">
                  <span className="font-semibold">CJ</span>
                </div>
              </div>
              <div>
                <div className="flex items-center">
                  <span className="font-medium">CJ</span>
                  <span className="text-gray-400 text-xs ml-2">just now</span>
                </div>
                <div className="mt-1 font-mono">
                  <div className="flex items-center">
                    <span>typing</span>
                    <div className="typing-cursor"></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Empty div for scrolling to bottom */}
          <div ref={messagesEndRef}></div>
        </div>
        
        {/* Chat Input */}
        <div className="absolute bottom-0 left-0 right-0 bg-[#222529] p-4 border-t border-gray-700">
          <div className="flex items-center">
            <div className="flex-1 relative">
              <input 
                ref={inputRef}
                type="text" 
                placeholder="Message CJ"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full bg-gray-700 text-white rounded-md py-3 px-4 outline-none focus:ring-2 focus:ring-cratejoy-teal font-mono"
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center space-x-2 text-gray-400">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 cursor-pointer hover:text-white" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 100-2 1 1 0 000 2zm7-1a1 1 0 11-2 0 1 1 0 012 0zm-.464 5.535a1 1 0 10-1.415-1.414 3 3 0 01-4.242 0 1 1 0 00-1.415 1.414 5 5 0 007.072 0z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
            <button 
              onClick={handleSendMessage}
              className="ml-3 bg-cratejoy-teal hover:bg-cratejoy-dark text-white px-4 py-3 rounded-md font-medium transition duration-200"
            >
              Send
            </button>
          </div>
          <div className="text-xs text-gray-400 mt-2">
            Press Enter to send, ESC to close
          </div>
        </div>
      </div>
    </>
  );
};

export default ChatDrawer;
