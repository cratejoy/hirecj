import React from 'react';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Shield } from 'lucide-react';

interface Persona {
  id: string;
  name: string;
  business: string;
}

interface Scenario {
  id: string;
  name: string;
  description: string;
}

interface ConfigurationBarProps {
  personas: Persona[];
  selectedPersona: string;
  onPersonaChange: (value: string) => void;
  scenarios: Scenario[];
  selectedScenario: string;
  onScenarioChange: (value: string) => void;
  trustLevel: number;
  onTrustLevelChange: (value: number) => void;
  showTrustLevel?: boolean;
}

export const ConfigurationBar: React.FC<ConfigurationBarProps> = ({
  personas,
  selectedPersona,
  onPersonaChange,
  scenarios,
  selectedScenario,
  onScenarioChange,
  trustLevel,
  onTrustLevelChange,
  showTrustLevel = true,
}) => {
  return (
    <div className="flex border-t">
      {/* Left Side - Persona */}
      <div className="flex-1 border-r p-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Persona:</span>
          <Select value={selectedPersona} onValueChange={onPersonaChange}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Select persona" />
            </SelectTrigger>
            <SelectContent>
              {personas.map(persona => (
                <SelectItem key={persona.id} value={persona.id}>
                  {persona.name} - {persona.business}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      
      {/* Middle - Scenario */}
      <div className="flex-1 border-r p-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Scenario:</span>
          <Select value={selectedScenario} onValueChange={onScenarioChange}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Select scenario" />
            </SelectTrigger>
            <SelectContent>
              {scenarios.map(scenario => (
                <SelectItem key={scenario.id} value={scenario.id}>
                  {scenario.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Right Side - Trust Level */}
      {showTrustLevel && (
        <div className="flex-1 p-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium flex items-center gap-1">
              <Shield className="h-3 w-3" />
              Trust Level:
            </span>
            <div className="flex-1 flex items-center gap-3">
              <Slider
                value={[trustLevel]}
                onValueChange={([value]) => onTrustLevelChange(value)}
                min={1}
                max={5}
                step={1}
                className="flex-1"
              />
              <span className="text-sm font-medium w-8 text-center">{trustLevel}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};