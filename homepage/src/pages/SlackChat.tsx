import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Link, useLocation, useSearch } from 'wouter';
import { motion } from 'framer-motion';
import { useChat } from '@/hooks/useChat';
import { useWebSocketChat } from '@/hooks/useWebSocketChat';
import { useUserSession } from '@/hooks/useUserSession';
import DemoScriptFlow from '@/components/DemoScriptFlow';
import { ConfigurationModal } from '@/components/ConfigurationModal';
import { ChatInterface } from '@/components/ChatInterface';
import { useToast } from '@/hooks/use-toast';
import { VALID_WORKFLOWS, WorkflowType, DEFAULT_WORKFLOW, WORKFLOW_NAMES } from '@/constants/workflow';

interface Message {
	id: string;
	sender: 'user' | 'cj';
	content: string;
	timestamp: string;
	ui_elements?: Array<{
		id: string;
		type: string;
		provider: string;
		placeholder: string;
	}>;
}

interface ChatConfig {
	scenarioId: string | null;
	merchantId: string | null;
	workflow: WorkflowType | null;
}

// Workflow display names with emojis for UI

const SlackChat = () => {
	const [location, setLocation] = useLocation();
	const searchString = useSearch();

	// --- DEBUG: log full page URL once on initial render -----------------
	useEffect(() => {
		console.log('[SlackChat] Full page URL on load:', window.location.href);
		console.log('[SlackChat] window.location.search:', window.location.search);
	}, []);
	// ---------------------------------------------------------------------

	const { toast } = useToast();
	const inputRef = useRef<HTMLInputElement>(null);
	const messagesEndRef = useRef<HTMLDivElement>(null);
	const [inputValue, setInputValue] = useState('');
	const [emailModalOpen, setEmailModalOpen] = useState(false);
	const [showDailyReport, setShowDailyReport] = useState(true);
	
	// Use the user session hook for persistent user state
	const userSession = useUserSession();
	
	// Always skip config modal
	const [showConfigModal, setShowConfigModal] = useState(false);
	
	// Log OAuth configuration on startup
	useEffect(() => {
		const authUrl = import.meta.env.VITE_AUTH_URL || 'https://amir-auth.hirecj.ai';
		console.log('🛍️ Shopify OAuth Configuration (on page load):');
		console.log('  Auth Service URL:', authUrl);
		console.log('  Expected Redirect URI:', `${authUrl}/api/v1/shopify/callback`);
		console.log('  Frontend URL:', window.location.origin);
	}, []);
	
	// Parse workflow from URL params
	const getWorkflowFromUrl = useCallback(() => {
		const params = new URLSearchParams(searchString);
		const urlWorkflow = params.get('workflow');
		
		if (urlWorkflow && VALID_WORKFLOWS.includes(urlWorkflow as any)) {
			return urlWorkflow as WorkflowType;
		}
		
		// Check localStorage for last used workflow
		const savedWorkflow = localStorage.getItem('lastWorkflow');
		if (savedWorkflow && VALID_WORKFLOWS.includes(savedWorkflow as any)) {
			return savedWorkflow as WorkflowType;
		}
		
		return DEFAULT_WORKFLOW;
	}, [searchString]);
	
	// Initialize chatConfig with URL workflow (merchant now in userSession)
	const [chatConfig, setChatConfig] = useState<ChatConfig>(() => {
		const params = new URLSearchParams(searchString);
		
		// Get merchantId and scenario from URL if present
		const urlMerchantId = params.get('merchantId');
		const urlScenario = params.get('scenario');
		
		return {
			scenarioId: urlScenario || null,
			merchantId: urlMerchantId || userSession.merchantId, // Use URL param if available, otherwise user session
			workflow: getWorkflowFromUrl()
		};
	});
	
	// Track if we're updating internally to prevent loops
	const isInternalUpdateRef = useRef(false);
	
	// Update URL when workflow changes
	useEffect(() => {
		if (chatConfig.workflow && !isInternalUpdateRef.current) {
			const params = new URLSearchParams(searchString);
			if (params.get('workflow') !== chatConfig.workflow) {
				params.set('workflow', chatConfig.workflow);
				setLocation(`${location}?${params.toString()}`, { replace: true });
			}
			localStorage.setItem('lastWorkflow', chatConfig.workflow);
		}
		// Reset flag after update
		isInternalUpdateRef.current = false;
	}, [chatConfig.workflow, location, searchString, setLocation]);
	

	// Sync userSession.merchantId to chatConfig when it changes
	useEffect(() => {
		setChatConfig(prev => ({
			...prev,
			merchantId: userSession.merchantId
		}));
	}, [userSession.merchantId]);
	

	const isRealChat = useMemo(() => {
		// Check if this is an OAuth return
		const params = new URLSearchParams(window.location.search);
		const isOAuthReturn = params.get('oauth') === 'complete';
		
		return !showConfigModal && !!chatConfig.workflow && 
			// For onboarding, support_daily, and OAuth returns, we don't need merchantId/scenarioId initially
			(chatConfig.workflow === 'shopify_onboarding' || 
			 chatConfig.workflow === 'support_daily' || 
			 chatConfig.workflow === 'shopify_post_auth' ||
			 isOAuthReturn ||
			 (!!chatConfig.scenarioId && !!chatConfig.merchantId));
	}, [showConfigModal, chatConfig]);


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
		merchantId: chatConfig.merchantId || '',
		scenario: chatConfig.scenarioId || '',
		workflow: chatConfig.workflow || 'ad_hoc_support',
		onError: handleChatError,
		onWorkflowUpdated: (newWorkflow, previousWorkflow) => {
			// Update local state
			setChatConfig(prev => ({ ...prev, workflow: newWorkflow as WorkflowType }));
			
			// Update URL to match confirmed workflow
			const params = new URLSearchParams(window.location.search);
			params.set('workflow', newWorkflow);
			const newUrl = `${window.location.pathname}?${params.toString()}`;
			window.history.replaceState({}, '', newUrl);
			
			console.log('[SlackChat] URL updated after workflow transition', { 
				from: previousWorkflow, 
				to: newWorkflow,
				url: newUrl 
			});
		},
		onOAuthProcessed: (data) => {
			if (data.success && data.merchant_id && data.shop_domain) {
				userSession.setMerchant(data.merchant_id, data.shop_domain);
				toast({
					title: "Connected to Shopify!",
					description: data.is_new ? "Welcome! Let me take a look at your store..." : "Welcome back! Good to see you again.",
					duration: 5000,
				});
			} else {
				toast({
					title: "Authentication Failed",
					description: "Failed to finalize Shopify connection.",
					variant: "destructive"
				});
			}
		}
	});
	

	// Use appropriate chat based on mode
	const messages = isRealChat ? wsChat.messages : demoChat.messages;
	const isTyping = isRealChat ? wsChat.isTyping : demoChat.isTyping;
	const handleSendMessage = isRealChat ? wsChat.sendMessage : demoChat.handleSendMessage;
	
	// Clean up OAuth-related URL params after processing
	useEffect(() => {
		const params = new URLSearchParams(window.location.search);
		// Clean up OAuth-related URL params after processing, but keep workflow
		if (params.has('oauth')) {
			params.delete('oauth');
			const newUrl = params.toString() ? `${window.location.pathname}?${params.toString()}` : window.location.pathname;
			window.history.replaceState({}, '', newUrl);
		}
	}, [location, searchString]); // Rerun if location changes.

	// Debug - only log when message count changes
	const prevMessageCountRef = useRef(messages.length);
	useEffect(() => {
		if (prevMessageCountRef.current !== messages.length) {
			console.log('[SlackChat] Messages length changed:', prevMessageCountRef.current, '->', messages.length);
			prevMessageCountRef.current = messages.length;
		}
	}, [messages.length]);

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

	// Setup debug interface
	useEffect(() => {
		// Always enable debug interface

		// Define the debug interface
		const debugInterface = {
			status: () => {
				console.group('%c📊 Current Status', 'color: #4CAF50; font-size: 14px; font-weight: bold');
				
				console.group('👤 User Session');
				console.log('Merchant ID:', userSession.merchantId || 'None');
				console.log('Shop Domain:', userSession.shopDomain || 'None');
				console.log('Authenticated:', userSession.isConnected ? '✅ Yes' : '❌ No');
				console.groupEnd();
				
				console.group('💬 Conversation');
				console.log('Workflow:', chatConfig.workflow || 'None');
				console.log('Scenario:', chatConfig.scenarioId || 'None');
				console.log('WebSocket:', wsChat.isConnected ? '✅ Connected' : '❌ Disconnected');
				console.log('Messages:', messages.length);
				console.groupEnd();
				
				console.groupEnd();
			},
			debug: () => {
				console.group('%c🤖 CJ Debug Snapshot', 'color: #00D4FF; font-size: 16px; font-weight: bold');
				
				console.group('📊 Session');
				console.log('Status:', wsChat.isConnected ? '✅ Connected' : '❌ Disconnected');
				console.log('Merchant:', chatConfig.merchantId || 'Not authenticated');
				console.log('Workflow:', chatConfig.workflow);
				console.log('Scenario:', chatConfig.scenarioId || 'None');
				console.groupEnd();
				
				console.group('💬 Conversation');
				console.log('Messages:', messages.length);
				console.log('Is Typing:', isTyping);
				console.log('Connection State:', wsChat.connectionState);
				console.groupEnd();
				
				console.groupEnd();
				
				// Request detailed state from backend
				if (wsChat.isConnected) {
					wsChat.sendSpecialMessage({
						type: 'debug_request',
						data: { type: 'snapshot' }
					});
				}
			},
			
			session: () => {
				if (wsChat.isConnected) {
					wsChat.sendSpecialMessage({
						type: 'debug_request',
						data: { type: 'session' }
					});
				} else {
					console.log('%c❌ Not connected to CJ', 'color: red');
				}
			},
			
			// Show the last 10 chat messages that CJ *received/sent*
			// (these are NOT the LLM prompts).
			history: () => {
				if (wsChat.isConnected) {
					wsChat.sendSpecialMessage({
						type: 'debug_request',
						data: { type: 'prompts' } // backend returns chat history
					});
				} else {
					console.log('%c❌ Not connected to CJ', 'color: red');
				}
			},
			// Deprecated alias kept for backward-compatibility
			prompts: () => {
				console.warn('⚠️  cj.prompts() is deprecated. Use cj.history() instead.');
				debugInterface.history();
			},
			
			context: () => {
				console.group('%c📝 Conversation Context', 'color: #00D4FF; font-size: 14px; font-weight: bold');
				console.log('Total Messages:', messages.length);
				
				if (messages.length > 0) {
					console.group('Recent Messages');
					messages.slice(-5).forEach((msg, idx) => {
						console.log(`[${idx + 1}] ${msg.sender}:`, msg.content.substring(0, 100) + '...');
					});
					console.groupEnd();
				}
				
				console.groupEnd();
			},
			
			events: () => {
				console.log('%c📡 Live events started...', 'color: #00D4FF');
				console.log('(Events will appear as they occur)');
				// Note: events will be logged by the WebSocket handler
			},
			
			stop: () => {
				console.log('%c📡 Live events stopped', 'color: #00D4FF');
			},
			
			help: () => {
				console.log('%c🤖 CJ Debug Commands:', 'color: #00D4FF; font-size: 14px; font-weight: bold');
				console.table({
					'cj.status()': 'Current user & conversation status',
					'cj.debug()': 'Full state snapshot',
					'cj.session()': 'Session & auth details',
					'cj.history()': 'Recent chat messages',
					'cj.context()': 'Conversation context',
					'cj.events()': 'Start live event stream',
					'cj.stop()': 'Stop event stream',
					'cj.help()': 'Show this help'
				});
			}
		};
		
		// Attach to window
		(window as any).cj = debugInterface;
		
		// Show debug interface ready message once
		console.log('%c🤖 CJ Debug Interface Ready! Type cj.help() for commands', 'color: #00D4FF; font-size: 14px; font-weight: bold');
		
		
	}, []); // Only run once on mount

	const handleMessageSend = () => {
		if (inputValue.trim()) {
			console.log('[UI] User submitting message:', inputValue.trim());
			handleSendMessage(inputValue);
			setInputValue('');
		}
	};

	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleMessageSend();
		}
	};

	const handleStartChat = useCallback((scenarioId: string, merchantId: string, workflow: 'ad_hoc_support' | 'daily_briefing' | 'support_daily') => {
		console.log('[SlackChat] Starting chat', {
			scenarioId,
			merchantId,
			workflow
		});

		// Update all config at once
		const config = {
			scenarioId,
			merchantId,
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
					
					{/* Workflow Switcher */}
					<div className="ml-6 flex items-center gap-2">
						<span className="text-sm text-gray-300">Workflow:</span>
						<select
							value={chatConfig.workflow || DEFAULT_WORKFLOW}
							onChange={(e) => {
								const newWorkflow = e.target.value as WorkflowType;
								// Update local state
								setChatConfig(prev => ({ ...prev, workflow: newWorkflow }));
								// Update URL 
								const params = new URLSearchParams(window.location.search);
								params.set('workflow', newWorkflow);
								window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
								// Trigger reconnect with new workflow
								window.location.reload();
							}}
							className="bg-gray-700 text-white text-sm px-3 py-1 rounded border border-gray-600 focus:border-blue-400 focus:outline-none hover:bg-gray-600 transition-colors"
						>
							{VALID_WORKFLOWS.map(workflow => (
								<option key={workflow} value={workflow}>
									{WORKFLOW_NAMES[workflow]}
								</option>
							))}
						</select>
					</div>
					{chatConfig.scenarioId && chatConfig.merchantId && (
						<span className="ml-2 sm:ml-4 text-xs sm:text-sm text-gray-300 truncate max-w-[200px] sm:max-w-none">
							{chatConfig.merchantId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} - {chatConfig.scenarioId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
						</span>
					)}
				</div>

				<div className="flex items-center space-x-2">
					{userSession.isConnected && (
						<>
							<span className="text-gray-400 text-sm mr-2 hidden sm:inline">
								{userSession.shopDomain}
							</span>
							<button
								onClick={() => {
									// Backend-driven logout
									if (wsChat.connectionState === 'connected') {
										wsChat.sendSpecialMessage({
											type: 'logout',
											data: {}
										});
									}
									
									// Clear local session
									userSession.clearMerchant();
									
									// Redirect to home after a short delay to ensure backend processing
									setTimeout(() => {
										window.location.href = '/';
									}, 100);
								}}
								className="text-gray-300 hover:text-white px-3 py-1 rounded text-sm bg-gray-700 hover:bg-gray-600 transition-colors"
							>
								Logout
							</button>
						</>
					)}
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
