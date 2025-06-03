import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Skeleton } from './ui/skeleton';
import { Clock, TrendingUp, MessageSquare, BarChart3, RefreshCw } from 'lucide-react';
import { useUniverses } from '@/hooks/useUniverses';

interface ConfigurationModalProps {
	isOpen: boolean;
	onClose: () => void;
	onStartChat: (scenarioId: string, merchantId: string, workflow: 'ad_hoc_support' | 'daily_briefing') => void;
}

export function ConfigurationModal({ isOpen, onClose, onStartChat }: ConfigurationModalProps) {
	const [selectedScenario, setSelectedScenario] = useState<any | null>(null);

	// Use the cached universes hook
	const { scenarios, loading, error, refetch } = useUniverses();

	const handleStartChat = (workflow: 'ad_hoc_support' | 'daily_briefing') => {
		if (selectedScenario) {
			onStartChat(selectedScenario.scenarioId, selectedScenario.merchantId, workflow);
		}
	};

	return (
		<Dialog open={isOpen} onOpenChange={onClose}>
			<DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
				<DialogHeader>
					<DialogTitle className="text-2xl font-bold">Choose Your Demo Scenario</DialogTitle>
				</DialogHeader>

				{error && (
					<Alert variant="destructive">
						<AlertDescription>{error}</AlertDescription>
					</Alert>
				)}

				<div className="space-y-6">
					<div className="flex items-center justify-between">
						<p className="text-gray-600">
							Select a pre-generated scenario to experience how CJ handles different merchant situations:
						</p>
						{!loading && (
							<Button
								variant="ghost"
								size="sm"
								onClick={() => refetch()}
								className="text-gray-500 hover:text-gray-700"
							>
								<RefreshCw className="h-4 w-4 mr-1" />
								Refresh
							</Button>
						)}
					</div>

					{loading ? (
						<div className="grid grid-cols-1 gap-4">
							{[1, 2].map(i => (
								<Skeleton key={i} className="h-32" />
							))}
						</div>
					) : scenarios.length === 0 ? (
						<Alert>
							<AlertDescription>
								No scenarios are currently available. Please check back later or contact support.
							</AlertDescription>
						</Alert>
					) : (
						<div className="grid grid-cols-1 gap-4">
							{scenarios.map(scenario => (
								<Card
									key={scenario.id}
									className={`cursor-pointer transition-all ${selectedScenario?.id === scenario.id
											? 'ring-2 ring-cratejoy-teal shadow-lg'
											: 'hover:shadow-md hover:border-gray-300'
										}`}
									onClick={() => setSelectedScenario(scenario)}
								>
									<CardHeader>
										<div className="flex items-start justify-between">
											<div className="flex-1">
												<CardTitle className="text-lg mb-1">{scenario.name}</CardTitle>
												<CardDescription className="text-sm">
													{scenario.description}
												</CardDescription>
											</div>
										</div>
									</CardHeader>
									<CardContent>
										<div className="flex flex-wrap gap-4 text-sm">
											<div className="flex items-center gap-1">
												<Clock className="w-4 h-4 text-gray-400" />
												<span className="text-gray-500">Avg daily tickets:</span>
												<span className="font-medium">{scenario.metrics.daily_tickets}</span>
											</div>
											<div className="flex items-center gap-1">
												<TrendingUp className="w-4 h-4 text-gray-400" />
												<span className="text-gray-500">Customers:</span>
												<span className="font-medium">{scenario.metrics.total_customers}</span>
											</div>
											<div className="flex items-center gap-1">
												<span className="text-gray-500">Timeline:</span>
												<span className="font-medium">{scenario.metrics.timeline_days} days</span>
											</div>
										</div>
									</CardContent>
								</Card>
							))}
						</div>
					)}

					{/* Workflow Selection */}
					{selectedScenario && (
						<div className="space-y-4 pt-4 border-t">
							<p className="text-sm text-gray-600 text-center">
								How would you like to start?
							</p>
							<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
								<Button
									onClick={() => handleStartChat('daily_briefing')}
									className="h-auto p-6 flex flex-col items-center gap-3 bg-gradient-to-br from-cratejoy-teal to-cratejoy-dark hover:from-cratejoy-dark hover:to-cratejoy-teal text-white transition-all duration-300"
								>
									<BarChart3 className="w-8 h-8" />
									<div className="space-y-1 text-center">
										<div className="font-semibold text-lg">Daily Flash Brief</div>
										<div className="text-xs opacity-90">CJ starts with metrics & insights</div>
									</div>
								</Button>

								<Button
									onClick={() => handleStartChat('ad_hoc_support')}
									className="h-auto p-6 flex flex-col items-center gap-3 bg-gradient-to-br from-linkedin-blue to-blue-700 hover:from-blue-700 hover:to-linkedin-blue text-white transition-all duration-300"
								>
									<MessageSquare className="w-8 h-8" />
									<div className="space-y-1 text-center">
										<div className="font-semibold text-lg">Direct Question</div>
										<div className="text-xs opacity-90">You start the conversation</div>
									</div>
								</Button>
							</div>
						</div>
					)}

					{!selectedScenario && (
						<div className="text-center text-sm text-gray-500 pt-4 border-t">
							Select a scenario above to continue
						</div>
					)}
				</div>
			</DialogContent>
		</Dialog>
	);
}