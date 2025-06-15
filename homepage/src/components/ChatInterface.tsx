import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ThumbsUp, ThumbsDown, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { logger } from '@/lib/logger';
import { FactCheckButton } from './FactCheckButton';
import { FactCheckModal } from './FactCheckModal';
import { MessageContent } from './MessageContent';
import { useFactCheck } from '@/hooks/useFactCheck';

const chatLogger = logger.child('chat');

interface Message {
	id: string;
	sender: 'user' | 'cj' | 'system';
	content: string;
	timestamp: string;
	metadata?: {
		metrics?: {
			prompts: number;
			tools: number;
			time: number;
		};
		turn?: number;
		messageIndex?: number;
		factCheckAvailable?: boolean;
		isThinking?: boolean;
	};
	ui_elements?: Array<{
		id: string;
		type: string;
		provider: string;
		placeholder: string;
	}>;
}

interface Progress {
	status: 'initializing' | 'creating agent' | 'generating response' | 'using tool';
	toolsCalled?: number;
	currentTool?: string;
	elapsed?: number;
}

interface ChatInterfaceProps {
	messages: Message[];
	isTyping: boolean;
	progress: Progress | null;
	merchantName: string;
	isConnected?: boolean;
	sendFactCheck?: (messageIndex: number) => void;
	cjVersion?: string;
}

export function ChatInterface({ messages, isTyping, progress, merchantName, isConnected, sendFactCheck, cjVersion = "v6.0.1" }: ChatInterfaceProps) {
	const { toast } = useToast();
	const [annotationModal, setAnnotationModal] = useState<{
		isOpen: boolean;
		messageId: string | null;
		messageIndex: number | null;
		sentiment: 'like' | 'dislike' | null;
	}>({ isOpen: false, messageId: null, messageIndex: null, sentiment: null });
	const [feedbackText, setFeedbackText] = useState('');
	const [annotations, setAnnotations] = useState<{ [key: string]: { sentiment: string, text: string, timestamp: string } }>({});

	// Fact-checking state using custom hook
	const { checkFact, isChecking, getCachedResults, handleFactCheckResult } = useFactCheck();
	const [factCheckModal, setFactCheckModal] = useState<{
		isOpen: boolean;
		messageIndex: number | null;
		results: any[] | null;
	}>({ isOpen: false, messageIndex: null, results: null });

	const [isLoadingAnnotations, setIsLoadingAnnotations] = useState(false);

	// TODO: Update annotation fetching to use session-based endpoints
	// For now, annotations are disabled until we update the backend API
	React.useEffect(() => {
		// Annotations temporarily disabled - will be re-enabled with session-based API
		setIsLoadingAnnotations(false);
	}, [isConnected]);

	// Prefill feedback text when opening modal for existing annotation
	React.useEffect(() => {
		if (annotationModal.isOpen && annotationModal.messageIndex !== null) {
			const existingAnnotation = annotations[String(annotationModal.messageIndex)];
			if (existingAnnotation?.text && existingAnnotation.sentiment === annotationModal.sentiment) {
				setFeedbackText(existingAnnotation.text);
			} else {
				setFeedbackText('');
			}
		}
	}, [annotationModal.isOpen, annotationModal.messageIndex, annotationModal.sentiment, annotations]);

	// Log message updates
	React.useEffect(() => {
		chatLogger.debug('Messages updated', {
			count: messages.length,
			messages: messages.map(m => ({
				id: m.id,
				sender: m.sender,
				preview: m.content.substring(0, 50) + '...',
				metadata: m.metadata
			}))
		});
	}, [messages]);

	const formatTimestamp = (timestamp: string) => {
		const date = new Date(timestamp);
		return date.toLocaleTimeString('en-US', {
			hour: 'numeric',
			minute: '2-digit',
			hour12: true
		});
	};

	const getProgressMessage = () => {
		if (!progress) return 'CJ is thinking...';

		const elapsed = progress.elapsed ? ` (${Math.round(progress.elapsed)}s)` : '';

		switch (progress.status) {
			case 'initializing':
				return `CJ is preparing to help...${elapsed}`;
			case 'creating agent':
				return `CJ is getting ready...${elapsed}`;
			case 'generating response':
				return `CJ is crafting a response...${elapsed}`;
			case 'using tool':
				const toolName = progress.currentTool || 'working on it';
				const toolCount = progress.toolsCalled ? ` (${progress.toolsCalled} tools used)` : '';
				return `CJ is ${toolName}...${toolCount}${elapsed}`;
			default:
				return `CJ is thinking...${elapsed}`;
		}
	};

	const handleFactCheck = async (messageIndex: number) => {
		if (!sendFactCheck) {
			toast({
				title: "Error",
				description: "Fact-checking is not available",
				variant: "destructive",
			});
			return;
		}

		// Check cache first
		const cachedResults = getCachedResults(messageIndex);
		if (cachedResults) {
			setFactCheckModal({
				isOpen: true,
				messageIndex,
				results: cachedResults
			});
			return;
		}

		// Open modal with loading state
		setFactCheckModal({
			isOpen: true,
			messageIndex,
			results: null
		});

		// Start fact check
		checkFact(messageIndex, sendFactCheck);

		// Temporary mock results - remove when WebSocket integration is complete
		setTimeout(() => {
			const mockResults = [
				{
					claim: "The support ticket volume increased by 15%",
					verdict: "verified",
					explanation: "Based on the data from the last 7 days, support tickets did increase by 15.2%",
					confidence: 0.95
				},
				{
					claim: "Most tickets are related to shipping issues",
					verdict: "unverifiable",
					explanation: "Insufficient data to verify the category breakdown of tickets",
					confidence: 0.4
				}
			];

			handleFactCheckResult(messageIndex, mockResults);
			setFactCheckModal(prev => ({
				...prev,
				results: mockResults
			}));
		}, 2000);
	};

	return (
		<div className="p-4 space-y-4">
			{/* Connection status */}
			{isConnected === false && (
				<div className="bg-yellow-900/20 border border-yellow-700 rounded-lg px-4 py-2 text-center">
					<p className="text-yellow-400 text-sm">
						Connecting to CJ... Please wait.
					</p>
				</div>
			)}

			{/* Welcome message */}
			{messages.length === 0 && isConnected && !isTyping && (
				<div className="text-center py-8">
					<p className="text-gray-400">
						You're now chatting with <span className="font-semibold">{merchantName}</span>
					</p>
					<p className="text-gray-500 text-sm mt-2">
						CJ is ready to help. Ask about support tickets, customer issues, or business metrics.
					</p>
				</div>
			)}

			{/* Messages */}
			<AnimatePresence>
				{messages.map((message) => (
					<motion.div
						key={message.id}
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
						exit={{ opacity: 0, y: -20 }}
						transition={{ duration: 0.3 }}
						className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
					>
						<div className={`flex items-start ${message.sender === 'user' ? 'flex-row-reverse' : ''}`}>
							{/* Avatar */}
							<div className={`flex-shrink-0 ${message.sender === 'user' ? 'ml-3' : 'mr-3'}`}>
								{message.sender === 'user' ? (
									<div className="w-8 h-8 bg-gray-600 rounded-lg flex items-center justify-center">
										<span className="text-white text-sm font-medium">
											Y
										</span>
									</div>
								) : (
									<img
										src="/images/cj-avatar-48.jpg"
										alt="CJ"
										className="w-8 h-8 rounded-lg object-cover"
									/>
								)}
							</div>

							{/* Message content */}
							<div className="max-w-xs sm:max-w-md">
								<div className="flex items-baseline mb-1">
									<span className="font-semibold text-sm mr-2">
										{message.sender === 'user' ? 'You' : `CJ - ${cjVersion}`}
									</span>
									<span className="text-xs text-gray-500">
										{formatTimestamp(message.timestamp)}
									</span>
								</div>
								<div
									className={`rounded-lg px-3 py-2 ${message.sender === 'user'
											? 'bg-blue-600 text-white'
											: 'bg-gray-700 text-gray-100'
										}`}
								>
									{message.metadata?.isThinking ? (
										<p className="text-sm italic opacity-75">
											{message.content}
										</p>
									) : message.sender === 'cj' ? (
										<MessageContent
											content={message.content}
											isThinking={message.metadata?.isThinking}
											ui_elements={message.ui_elements}
										/>
									) : (
										<div className="text-sm prose prose-sm max-w-none prose-invert">
											<ReactMarkdown 
												remarkPlugins={[remarkBreaks]}
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
												{message.content}
											</ReactMarkdown>
										</div>
									)}
								</div>

								{/* Annotation buttons for CJ messages */}
								{message.sender === 'cj' && !message.metadata?.isThinking && (
									<div className="flex items-center gap-2 mt-2">
										{(() => {
											const messageIndex = message.metadata?.messageIndex;
											const annotation = messageIndex !== undefined ? annotations[String(messageIndex)] : undefined;
											const hasLiked = annotation?.sentiment === 'like';
											const hasDisliked = annotation?.sentiment === 'dislike';

											return (
												<>
													<button
														onClick={() => {
															setAnnotationModal({
																isOpen: true,
																messageId: message.id,
																messageIndex: message.metadata?.messageIndex ?? null,
																sentiment: 'like'
															});
														}}
														disabled={isLoadingAnnotations}
														className={`flex items-center gap-1 text-xs transition-colors ${hasLiked
																? 'text-green-400'
																: 'text-gray-400 hover:text-green-400'
															} disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation p-1 -m-1`}
													>
														<ThumbsUp className={`w-3 h-3 ${hasLiked ? 'fill-current' : ''}`} />
														<span className="hidden sm:inline">Helpful</span>
													</button>
													<button
														onClick={() => {
															setAnnotationModal({
																isOpen: true,
																messageId: message.id,
																messageIndex: message.metadata?.messageIndex ?? null,
																sentiment: 'dislike'
															});
														}}
														disabled={isLoadingAnnotations}
														className={`flex items-center gap-1 text-xs transition-colors ${hasDisliked
																? 'text-red-400'
																: 'text-gray-400 hover:text-red-400'
															} disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation p-1 -m-1`}
													>
														<ThumbsDown className={`w-3 h-3 ${hasDisliked ? 'fill-current' : ''}`} />
														<span className="hidden sm:inline">Not helpful</span>
													</button>

													{/* Fact Check Button */}
													{message.metadata?.factCheckAvailable && (
														<FactCheckButton
															messageIndex={message.metadata.messageIndex ?? 0}
															isAvailable={true}
															isChecking={isChecking(message.metadata.messageIndex ?? 0)}
															hasResults={getCachedResults(message.metadata.messageIndex ?? 0) !== null}
															onClick={() => {
																const msgIndex = message.metadata?.messageIndex;
																if (msgIndex !== undefined) {
																	handleFactCheck(msgIndex);
																}
															}}
														/>
													)}

													{annotation?.text && (
														<>
															<span className="text-xs text-gray-500 italic ml-2">
																"{annotation.text.substring(0, 30)}{annotation.text.length > 30 ? '...' : ''}"
															</span>
															<button
																onClick={async () => {
																	if (messageIndex !== undefined) {
																		try {
																			// TODO: Update to use session-based API
																			// const BACKEND_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
																			// const response = await fetch(
																			// 	`${BACKEND_URL}/api/v1/annotations/${messageIndex}`,
																			// 	{ method: 'DELETE', credentials: 'include' }
																			// );

																			// Temporary mock - just update local state
																			const response = { ok: true };
																			
																			if (response.ok) {
																				setAnnotations(prev => {
																					const newAnnotations = { ...prev };
																					delete newAnnotations[String(messageIndex)];
																					return newAnnotations;
																				});

																				toast({
																					title: "Feedback removed",
																					description: "Your annotation has been deleted.",
																				});
																			}
																		} catch (error) {
																			chatLogger.error('Error deleting annotation', error);
																			toast({
																				title: "Error",
																				description: "Failed to remove feedback.",
																				variant: "destructive",
																			});
																		}
																	}
																}}
																className="text-xs text-gray-500 hover:text-red-400 ml-1"
															>
																(remove)
															</button>
														</>
													)}
												</>
											);
										})()}
									</div>
								)}
							</div>
						</div>
					</motion.div>
				))}
			</AnimatePresence>

			{/* Typing indicator */}
			{isTyping && (
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					exit={{ opacity: 0, y: -20 }}
					className="flex items-start"
				>
					<img
						src="/images/cj-avatar-48.jpg"
						alt="CJ"
						className="w-8 h-8 rounded-lg object-cover mr-3"
					/>
					<div className="bg-gray-700 rounded-lg px-3 py-2">
						<p className="text-sm text-gray-300 italic">
							{getProgressMessage()}
						</p>
						{progress && (
							<div className="mt-1">
								{progress.toolsCalled && progress.toolsCalled > 0 && (
									<p className="text-xs text-gray-500">
										Tools used: {progress.toolsCalled}
									</p>
								)}
								<div className="w-full bg-gray-600 rounded-full h-1 mt-2">
									<div
										className="bg-cratejoy-teal h-1 rounded-full transition-all duration-500"
										style={{
											width: progress.elapsed
												? `${Math.min((progress.elapsed / 10) * 100, 95)}%`
												: '10%'
										}}
									/>
								</div>
							</div>
						)}
					</div>
				</motion.div>
			)}

			{/* Annotation Modal */}
			<Dialog
				open={annotationModal.isOpen}
				onOpenChange={(open) => {
					setAnnotationModal({ isOpen: open, messageId: null, messageIndex: null, sentiment: null });
					setFeedbackText('');
				}}
			>
				<DialogContent className="sm:max-w-[500px]">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2">
							{annotationModal.sentiment === 'like' && (
								<>
									<ThumbsUp className="w-5 h-5 text-green-500" />
									<span>What made this response helpful?</span>
								</>
							)}
							{annotationModal.sentiment === 'dislike' && (
								<>
									<ThumbsDown className="w-5 h-5 text-red-500" />
									<span>What could be improved?</span>
								</>
							)}
							{!annotationModal.sentiment && (
								<>
									<MessageSquare className="w-5 h-5 text-blue-500" />
									<span>Share your feedback</span>
								</>
							)}
						</DialogTitle>
					</DialogHeader>

					<div className="space-y-4">
						<Textarea
							placeholder={
								annotationModal.sentiment === 'like'
									? "e.g., Clear explanation, accurate information, helpful suggestions..."
									: annotationModal.sentiment === 'dislike'
										? "e.g., Missing information, unclear response, incorrect details..."
										: "Share any feedback about this response..."
							}
							value={feedbackText}
							onChange={(e) => setFeedbackText(e.target.value)}
							className="min-h-[120px] resize-none"
						/>

						<div className="flex justify-end gap-2">
							<Button
								variant="outline"
								onClick={() => {
									setAnnotationModal({ isOpen: false, messageId: null, messageIndex: null, sentiment: null });
									setFeedbackText('');
								}}
							>
								Cancel
							</Button>
							<Button
								onClick={async () => {
									try {
										if (!annotationModal.messageIndex && annotationModal.messageIndex !== 0) {
											throw new Error('Message index not available');
										}

										// TODO: Update to use session-based API
										// const BACKEND_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
										// const response = await fetch(
										// 	`${BACKEND_URL}/api/v1/annotations/${annotationModal.messageIndex}`,
										// 	{
										// 		method: 'POST',
										// 		headers: {
										// 			'Content-Type': 'application/json',
										// 		},
										// 		body: JSON.stringify({
										// 			sentiment: annotationModal.sentiment || 'like',
										// 			text: feedbackText || undefined
										// 		}),
										// 		credentials: 'include' // Include cookies for session
										// 	}
										// );
										
										// Temporary mock response
										const response = { ok: true };
										const result = { annotation: { sentiment: annotationModal.sentiment, text: feedbackText, timestamp: new Date().toISOString() } };

										if (!response.ok) {
											throw new Error('Failed to submit annotation');
										}

										// const result = await response.json();

										// Update local annotations state
										if (annotationModal.messageIndex !== null) {
											const newAnnotation = {
												sentiment: result.annotation.sentiment || 'like',
												text: result.annotation.text || '',
												timestamp: result.annotation.timestamp || new Date().toISOString()
											};
											setAnnotations(prev => ({
												...prev,
												[String(annotationModal.messageIndex)]: newAnnotation
											}));
										}

										// Success - close modal and reset
										setAnnotationModal({ isOpen: false, messageId: null, messageIndex: null, sentiment: null });
										setFeedbackText('');

										// Show success toast
										toast({
											title: "Feedback submitted",
											description: "Thank you for helping CJ improve!",
										});
									} catch (error) {
										chatLogger.error('Error submitting annotation', error);

										// Show error toast
										toast({
											title: "Error",
											description: "Failed to submit feedback. Please try again.",
											variant: "destructive",
										});
									}
								}}
								className="bg-cratejoy-teal hover:bg-cratejoy-dark"
								disabled={!feedbackText.trim()}
							>
								Submit Feedback
							</Button>
						</div>
					</div>
				</DialogContent>
			</Dialog>

			{/* Fact Check Modal */}
			<FactCheckModal
				isOpen={factCheckModal.isOpen}
				onClose={() => setFactCheckModal(prev => ({ ...prev, isOpen: false }))}
				results={factCheckModal.results}
				isLoading={factCheckModal.results === null && factCheckModal.messageIndex !== null && isChecking(factCheckModal.messageIndex)}
				error={null}
			/>
		</div>
	);
}
