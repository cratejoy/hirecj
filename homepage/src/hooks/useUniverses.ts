import { useState, useEffect } from 'react';

interface Universe {
  merchant: string;
  scenario: string;
  version: string;
  filename: string;
  business_context: {
    current_state: {
      mrr: number;
      subscriber_count: number;
      churn_rate: number;
      csat_score: number;
      support_tickets_per_day: number;
      average_response_time_hours: number;
    };
    subscription_tiers?: Array<{
      name: string;
      price: number;
      active_subscribers: number;
    }>;
  };
  total_customers: number;
  total_tickets: number;
  days: number;
}

interface TransformedScenario {
  id: string;
  merchantId: string;
  scenarioId: string;
  name: string;
  description: string;
  metrics: {
    daily_tickets: number;
    total_customers: number;
    timeline_days: number;
  };
}

// Cache data in memory (persists across component mounts)
let cachedScenarios: TransformedScenario[] | null = null;
let cacheTimestamp: number | null = null;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export function useUniverses() {
  const [scenarios, setScenarios] = useState<TransformedScenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

  const fetchUniverses = async (forceRefresh = false) => {
    // Check cache first
    if (!forceRefresh && cachedScenarios && cacheTimestamp && 
        Date.now() - cacheTimestamp < CACHE_DURATION) {
      setScenarios(cachedScenarios);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/universes/`);

      if (!response.ok) {
        throw new Error('Failed to fetch universes');
      }

      const data: Universe[] = await response.json();
      
      // Transform universe data into selectable scenarios
      const transformedScenarios: TransformedScenario[] = data.map(universe => {
        // Create readable names from the IDs
        const merchantName = universe.merchant
          .replace(/_/g, ' ')
          .replace(/\b\w/g, l => l.toUpperCase());
        const scenarioName = universe.scenario
          .replace(/_/g, ' ')
          .replace(/\b\w/g, l => l.toUpperCase());
        
        // Calculate daily tickets (total tickets / timeline days)
        const dailyTickets = Math.round(universe.total_tickets / universe.days);
        
        return {
          id: `${universe.merchant}_${universe.scenario}`,
          merchantId: universe.merchant,
          scenarioId: universe.scenario,
          name: `${merchantName} - ${scenarioName}`,
          description: `MRR: $${universe.business_context.current_state.mrr.toLocaleString()} | CSAT: ${universe.business_context.current_state.csat_score}/5`,
          metrics: {
            daily_tickets: dailyTickets,
            total_customers: universe.total_customers,
            timeline_days: universe.days
          }
        };
      });
      
      // Update cache
      cachedScenarios = transformedScenarios;
      cacheTimestamp = Date.now();
      
      setScenarios(transformedScenarios);
    } catch (err) {
      setError('Unable to load available scenarios. Please try again.');
      console.error('Error fetching universes:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUniverses();
  }, []);

  return { scenarios, loading, error, refetch: () => fetchUniverses(true) };
}