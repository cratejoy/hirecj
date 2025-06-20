import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ConversationSummary } from '@/types/evals';
import { FileText, Calendar, MessageSquare, Wrench, Database, Search, Filter } from 'lucide-react';

interface ConversationListProps {
  conversations: ConversationSummary[];
  onSelect: (conversation: ConversationSummary) => void;
  selectedId?: string;
}

export function ConversationList({ conversations, onSelect, selectedId }: ConversationListProps) {
  const [search, setSearch] = useState('');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [workflowFilter, setWorkflowFilter] = useState<string>('all');

  // Get unique workflows for filter
  const workflows = Array.from(new Set(conversations.map(c => c.workflow)));

  // Apply filters
  const filteredConversations = conversations.filter(conv => {
    if (search && !conv.id.toLowerCase().includes(search.toLowerCase()) && 
        !conv.workflow.toLowerCase().includes(search.toLowerCase()) &&
        (!conv.persona || !conv.persona.toLowerCase().includes(search.toLowerCase()))) {
      return false;
    }
    if (sourceFilter !== 'all' && conv.source !== sourceFilter) {
      return false;
    }
    if (workflowFilter !== 'all' && conv.workflow !== workflowFilter) {
      return false;
    }
    return true;
  });

  // Group by date
  const groupedByDate = filteredConversations.reduce((acc, conv) => {
    const date = new Date(conv.timestamp).toLocaleDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(conv);
    return acc;
  }, {} as Record<string, ConversationSummary[]>);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold mb-2">Captured Conversations</h2>
        <p className="text-muted-foreground">
          Select a conversation to convert into eval test cases
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <div className="flex-1">
              <Input
                placeholder="Search conversations..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-9"
              />
            </div>
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger className="w-[140px] h-9">
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sources</SelectItem>
                <SelectItem value="playground">Playground</SelectItem>
                <SelectItem value="production">Production</SelectItem>
                <SelectItem value="synthetic">Synthetic</SelectItem>
              </SelectContent>
            </Select>
            <Select value={workflowFilter} onValueChange={setWorkflowFilter}>
              <SelectTrigger className="w-[180px] h-9">
                <SelectValue placeholder="Workflow" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Workflows</SelectItem>
                {workflows.map(workflow => (
                  <SelectItem key={workflow} value={workflow}>
                    {workflow}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Filter className="h-3 w-3" />
            Showing {filteredConversations.length} of {conversations.length} conversations
          </div>
        </CardContent>
      </Card>

      {/* Conversation List */}
      <div className="space-y-4">
        {Object.entries(groupedByDate).map(([date, dateConversations]) => (
          <div key={date} className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium">
              <Calendar className="h-4 w-4" />
              {date}
            </div>
            
            <div className="space-y-2">
              {dateConversations.map(conv => (
                <Card 
                  key={conv.id}
                  className={`cursor-pointer transition-colors hover:bg-accent/50 ${
                    selectedId === conv.id ? 'ring-2 ring-primary' : ''
                  }`}
                  onClick={() => onSelect(conv)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-base font-medium">
                          {conv.id.substring(0, 8)}...
                        </CardTitle>
                        <CardDescription className="text-xs">
                          {new Date(conv.timestamp).toLocaleTimeString()}
                        </CardDescription>
                      </div>
                      <div className="flex gap-1">
                        <Badge variant="outline" className="text-xs">
                          {conv.source}
                        </Badge>
                        <Badge variant="secondary" className="text-xs">
                          {conv.workflow}
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" />
                        {conv.message_count} messages
                      </div>
                      {conv.has_tool_calls && (
                        <div className="flex items-center gap-1">
                          <Wrench className="h-3 w-3" />
                          Tools used
                        </div>
                      )}
                      {conv.has_grounding && (
                        <div className="flex items-center gap-1">
                          <Database className="h-3 w-3" />
                          Grounding
                        </div>
                      )}
                    </div>
                    {conv.persona && (
                      <div className="mt-2">
                        <Badge variant="outline" className="text-xs">
                          Persona: {conv.persona}
                        </Badge>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
        
        {filteredConversations.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-8 text-center">
              <FileText className="h-8 w-8 text-muted-foreground mb-2" />
              <p className="text-muted-foreground">
                {conversations.length === 0 
                  ? 'No conversations captured yet' 
                  : 'No conversations match your filters'}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Capture conversations from the Playground to get started
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}