/**
 * Workflow-related constants
 */

// Valid workflow types
export const VALID_WORKFLOWS = [
  'ad_hoc_support',
  'daily_briefing',
  'shopify_onboarding',
  'support_daily',
  'shopify_post_auth',   // new post-OAuth workflow
] as const;

// TypeScript type derived from the constant array
export type WorkflowType = typeof VALID_WORKFLOWS[number];

// Workflow display names
export const WORKFLOW_NAMES: Record<WorkflowType, string> = {
  'ad_hoc_support': 'General Support',
  'daily_briefing': 'Daily Briefing',
  'shopify_onboarding': 'Shopify Onboarding',
  'support_daily': 'Support Daily',
  'shopify_post_auth': 'Post-Auth Overview',
};

// Workflow transition settings
export const WORKFLOW_TRANSITION_DEBOUNCE_MS = 100;  // Milliseconds to debounce workflow transitions

// Default workflow
export const DEFAULT_WORKFLOW: WorkflowType = 'shopify_onboarding';
