import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Link, useLocation } from 'wouter';
import { motion } from 'framer-motion';
import { useChat } from '@/hooks/useChat';
import { useWebSocketChat } from '@/hooks/useWebSocketChat';
import DemoScriptFlow from '@/components/DemoScriptFlow';
import { ConfigurationModal } from '@/components/ConfigurationModal';
import { ChatInterface } from '@/components/ChatInterface';
import { v4 as uuidv4 } from 'uuid';
import { useToast } from '@/hooks/use-toast';

interface Message {
	id: string;
	sender: 'user' | 'cj';
	content: string;
	timestamp: string;
}

interface ChatConfig {
	scenarioId: string | null;
	merchantId: string | null;
	conversationId: string;
	workflow: 'ad_hoc_support' | 'daily_briefing' | 'shopify_onboarding' | null;
}

const SlackChat = () => {
	const [, setLocation] = useLocation();
	const { toast } = useToast();
	const inputRef = useRef<HTMLInputElement>(null);
	const messagesEndRef = useRef<HTMLDivElement>(null);
	const [inputValue, setInputValue] = useState('');
	const [emailModalOpen, setEmailModalOpen] = useState(false);
	const [showDailyReport, setShowDailyReport] = useState(true);
	
	// Always skip config modal
	const [showConfigModal] = useState(false);
	
	// Update initial chatConfig
	const [chatConfig, setChatConfig] = useState<ChatConfig>({
		scenarioId: null, // No demo scenario
		merchantId: null, // Will be set after OAuth
		conversationId: uuidv4(),
		workflow: 'shopify_onboarding' // Always start with onboarding
	});
	

	const isRealChat = useMemo(() =>
		!showConfigModal && !!chatConfig.conversationId && !!chatConfig.workflow && 
		// For onboarding workflow, we don't need merchantId/scenarioId initially
		(chatConfig.workflow === 'shopify_onboarding' || (!!chatConfig.scenarioId && !!chatConfig.merchantId)),
		[showConfigModal, chatConfig]
	);

	console.log('[SlackChat] Component render', {
		showConfigModal,
		isRealChat,
		conversationId: chatConfig.conversationId,
		scenarioId: chatConfig.scenarioId,
		merchantId: chatConfig.merchantId,
		workflow: chatConfig.workflow
	});

	// Use demo chat for script flow
	const demoChat = useChat(setEmailModalOpen);

	// Memoize error handler to prevent re-renders
	const handleChatError = useCallback((error: string) => {
		console.error('Chat error:', error);

		// Check for specific error types
		if (error.toLowerCase().includes('universe not found')) {
			toast({
				title: "Configuration Error",
				description: "The selected scenario is no longer available. Please choose another.",
				variant: "destructive",
				duration: 5000,
			});
			// Reset to configuration modal
			setShowConfigModal(true);
		} else if (error.toLowerCase().includes('unable to connect')) {
			toast({
				title: "Connection Failed",
				description: "Unable to establish connection. Please check your internet and try again.",
				variant: "destructive",
				duration: 5000,
			});
		} else {
			toast({
				title: "Connection Error",
				description: error,
				variant: "destructive",
				duration: 5000,
			});
		}
	}, [toast]);

	// Use WebSocket chat for real conversations (only when ready)
	const wsChat = useWebSocketChat({
		enabled: isRealChat,
		conversationId: chatConfig.conversationId,
		merchantId: chatConfig.merchantId || '',
		scenario: chatConfig.scenarioId || '',
		workflow: chatConfig.workflow || 'ad_hoc_support',
		onError: handleChatError
	});
	
	// Debug WebSocket connection
	console.log('[SlackChat] WebSocket params:', {
		enabled: isRealChat,
		conversationId: chatConfig.conversationId,
		merchantId: chatConfig.merchantId || '',
		scenario: chatConfig.scenarioId || '',
		workflow: chatConfig.workflow || 'ad_hoc_support'
	});

	// Use appropriate chat based on mode
	const messages = isRealChat ? wsChat.messages : demoChat.messages;
	const isTyping = isRealChat ? wsChat.isTyping : demoChat.isTyping;
	const handleSendMessage = isRealChat ? wsChat.sendMessage : demoChat.handleSendMessage;

	// Debug
	console.log('[SlackChat] Messages length:', messages.length, 'isTyping:', isTyping);

	// Focus input when component mounts
	useEffect(() => {
		if (inputRef.current && !showConfigModal) {
			inputRef.current.focus();
		}
	}, [showConfigModal]);

	// Scroll to bottom when messages change
	useEffect(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
	}, [messages, isTyping]);

	// Save conversation on page unload
	useEffect(() => {
		const handleBeforeUnload = () => {
			if (isRealChat) {
				wsChat.endConversation();
			}
		};

		window.addEventListener('beforeunload', handleBeforeUnload);
		return () => {
			window.removeEventListener('beforeunload', handleBeforeUnload);
		};
	}, [isRealChat, wsChat]);

	const handleMessageSend = () => {
		if (inputValue.trim()) {
			console.log('[UI] User submitting message:', inputValue.trim());
			handleSendMessage(inputValue);
			setInputValue('');
		}
	};

	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e.key === 'Enter') {
			handleMessageSend();
		}
	};

	const handleStartChat = useCallback((scenarioId: string, merchantId: string, workflow: 'ad_hoc_support' | 'daily_briefing') => {
		const conversationId = uuidv4();

		console.log('[SlackChat] Starting chat', {
			scenarioId,
			merchantId,
			workflow,
			conversationId
		});

		// Update all config at once
		const config = {
			scenarioId,
			merchantId,
			conversationId,
			workflow
		};

		setChatConfig(config);
		setShowConfigModal(false);
	}, []);

	return (
		<div className="flex flex-col min-h-screen h-screen bg-chat-bg text-white overflow-hidden">
			{/* Configuration Modal */}
			<ConfigurationModal
				isOpen={showConfigModal}
				onClose={() => {
					setShowConfigModal(false);
					// If they close without selecting, go back to home
					if (!chatConfig.scenarioId || !chatConfig.merchantId) {
						setLocation('/');
					}
				}}
				onStartChat={handleStartChat}
			/>

			{/* Slack Header */}
			<header className="bg-slack-purple px-4 py-2 flex items-center justify-between">
				<div className="flex items-center">
					{/* Back button */}
					<button
						onClick={() => setLocation('/')}
						className="mr-4 text-gray-300 hover:text-white"
					>
						<svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</button>

					<div className="text-lg sm:text-xl font-bold">HireCJ</div>
					{chatConfig.scenarioId && chatConfig.merchantId && (
						<span className="ml-2 sm:ml-4 text-xs sm:text-sm text-gray-300 truncate max-w-[200px] sm:max-w-none">
							{chatConfig.merchantId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} - {chatConfig.scenarioId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
						</span>
					)}
				</div>

				<div className="flex items-center space-x-2">
					{isRealChat && (
						<button
							onClick={() => {
								wsChat.endConversation();
								toast({
									title: "Chat ended",
									description: "Your conversation has been ended.",
								});
								setShowConfigModal(true);
							}}
							className="text-gray-300 hover:text-white px-3 py-1 rounded text-sm bg-gray-700"
						>
							End Chat
						</button>
					)}
					<button className="text-gray-300 hover:text-white">
						<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
						</svg>
					</button>
					<button className="text-gray-300 hover:text-white">
						<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
						</svg>
					</button>
				</div>
			</header>

			{/* Slack Main Content */}
			<div className="flex flex-1 overflow-hidden">
				{/* Sidebar */}
				<aside className="w-60 bg-chat-sidebar hidden md:block p-4">
					<div className="mb-6">
						<h2 className="text-white text-lg font-semibold mb-2">Channels</h2>
						<ul className="space-y-1">
							<li className="flex items-center text-gray-300 hover:text-white bg-slack-purple rounded px-2 py-1">
								<span className="text-gray-500 mr-2">#</span>
								<span>making-money</span>
							</li>
							<li className="flex items-center text-gray-300 hover:text-white px-2 py-1">
								<span className="text-gray-500 mr-2">#</span>
								<span>support-help</span>
							</li>
							<li className="flex items-center text-gray-300 hover:text-white px-2 py-1">
								<span className="text-gray-500 mr-2">#</span>
								<span>customer-love</span>
							</li>
						</ul>
					</div>
					<div className="border-t border-gray-700 pt-4">
						<h2 className="text-white text-lg font-semibold mb-2">Direct Messages</h2>
						<ul className="space-y-1">
							<li className="flex items-center text-gray-300 hover:text-white px-2 py-1 bg-slack-purple rounded">
								<div className="w-2 h-2 bg-green-400 rounded-full mr-2"></div>
								<span>CJ (HireCJ)</span>
							</li>
							<li className="flex items-center text-gray-300 hover:text-white px-2 py-1">
								<div className="w-2 h-2 bg-gray-500 rounded-full mr-2"></div>
								<span>You</span>
							</li>
						</ul>
					</div>
				</aside>

				{/* Chat area */}
				<main className="flex-1 overflow-y-auto bg-chat-bg">
					<div className="max-w-3xl mx-auto">
						{/* If using real chat, we'll show WebSocket messages */}
						{isRealChat ? (
							<ChatInterface
								messages={messages}
								isTyping={isTyping}
								progress={wsChat.progress}
								merchantName={chatConfig.merchantId?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Merchant'}
								isConnected={wsChat.isConnected}
								conversationId={chatConfig.conversationId}
								sendFactCheck={wsChat.sendFactCheck}
							/>
						) : (
							/* Demo script flow for non-configured chat */
							<DemoScriptFlow
								onComplete={() => setShowConfigModal(true)}
							/>
						)}

						<div ref={messagesEndRef}></div>
					</div>

					{/* Show input field only for real chat */}
					{isRealChat && (
						<div className="sticky bottom-0 p-4 bg-chat-bg border-t border-gray-700">
							<div className="max-w-3xl mx-auto">
								<div className="flex items-center bg-gray-800 rounded-lg px-4 py-2">
									<input
										ref={inputRef}
										type="text"
										value={inputValue}
										onChange={(e) => setInputValue(e.target.value)}
										onKeyDown={handleKeyDown}
										placeholder="Type a message..."
										className="flex-1 bg-transparent text-white placeholder-gray-400 outline-none"
									/>
									<button
										onClick={handleMessageSend}
										className="ml-2 text-gray-400 hover:text-white transition-colors"
									>
										<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
											<path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
										</svg>
									</button>
								</div>
							</div>
						</div>
					)}
				</main>
			</div>
		</div>
	);
};

export default SlackChat;