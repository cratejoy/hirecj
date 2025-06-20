import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { ConversationList } from '@/components/evals/ConversationList';
import { EvalCaseEditor } from '@/components/evals/EvalCaseEditor';
import { EvalPreview } from '@/components/evals/EvalPreview';
import { DatasetManager } from '@/components/evals/DatasetManager';
import { ConversationSummary, EvalCase, EvalDataset, EvalDesignerState } from '@/types/evals';
import { useToast } from '@/components/ui/use-toast';
import { FileText, Save, Play, FolderOpen, Plus } from 'lucide-react';

export function EvalDesignerView() {
  const { toast } = useToast();
  const [state, setState] = useState<EvalDesignerState>({
    editingCases: [],
  });

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [datasets, setDatasets] = useState<EvalDataset[]>([]);
  const [activeTab, setActiveTab] = useState<'conversations' | 'cases' | 'preview' | 'datasets'>('conversations');

  // Load available conversations
  useEffect(() => {
    loadConversations();
    loadDatasets();
  }, []);

  const loadConversations = async () => {
    try {
      const response = await fetch('/api/v1/evals/conversations');
      if (response.ok) {
        const data = await response.json();
        setConversations(data.conversations);
      }
    } catch (error) {
      toast({
        title: 'Error loading conversations',
        description: 'Failed to load captured conversations',
        variant: 'destructive',
      });
    }
  };

  const loadDatasets = async () => {
    try {
      const response = await fetch('/api/v1/evals/datasets');
      if (response.ok) {
        const data = await response.json();
        setDatasets(data.datasets);
      }
    } catch (error) {
      toast({
        title: 'Error loading datasets',
        description: 'Failed to load eval datasets',
        variant: 'destructive',
      });
    }
  };

  const handleConversationSelect = async (conversation: ConversationSummary) => {
    setState(prev => ({ ...prev, selectedConversation: conversation }));
    
    // Load the full conversation and convert to cases
    try {
      const response = await fetch(`/api/v1/evals/conversations/${conversation.id}/convert`);
      if (response.ok) {
        const data = await response.json();
        setState(prev => ({ 
          ...prev, 
          editingCases: data.cases,
          selectedConversation: conversation 
        }));
        setActiveTab('cases');
        toast({
          title: 'Conversation loaded',
          description: `Created ${data.cases.length} eval cases from conversation`,
        });
      }
    } catch (error) {
      toast({
        title: 'Error converting conversation',
        description: 'Failed to convert conversation to eval cases',
        variant: 'destructive',
      });
    }
  };

  const handleCaseUpdate = (index: number, updatedCase: EvalCase) => {
    setState(prev => ({
      ...prev,
      editingCases: prev.editingCases.map((c, i) => i === index ? updatedCase : c)
    }));
  };

  const handleSaveToDataset = async (datasetId?: string) => {
    if (state.editingCases.length === 0) {
      toast({
        title: 'No cases to save',
        description: 'Create some eval cases first',
        variant: 'destructive',
      });
      return;
    }

    try {
      const response = await fetch('/api/v1/evals/datasets/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: datasetId || 'new',
          cases: state.editingCases,
          metadata: {
            source_conversation: state.selectedConversation?.id,
          }
        }),
      });

      if (response.ok) {
        const data = await response.json();
        toast({
          title: 'Dataset saved',
          description: `Saved ${state.editingCases.length} cases to dataset`,
        });
        loadDatasets();
        setActiveTab('datasets');
      }
    } catch (error) {
      toast({
        title: 'Error saving dataset',
        description: 'Failed to save eval cases to dataset',
        variant: 'destructive',
      });
    }
  };

  const handlePreviewRun = async () => {
    if (state.editingCases.length === 0) {
      toast({
        title: 'No cases to preview',
        description: 'Create some eval cases first',
        variant: 'destructive',
      });
      return;
    }

    try {
      const response = await fetch('/api/v1/evals/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cases: state.editingCases }),
      });

      if (response.ok) {
        const data = await response.json();
        setState(prev => ({ ...prev, previewResults: data.results }));
        setActiveTab('preview');
      }
    } catch (error) {
      toast({
        title: 'Error running preview',
        description: 'Failed to preview eval execution',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="flex h-full">
      {/* Sidebar Navigation */}
      <div className="w-64 border-r bg-muted/30">
        <div className="p-4 space-y-2">
          <h2 className="text-lg font-semibold mb-4">Eval Designer</h2>
          
          <Button 
            variant={activeTab === 'conversations' ? 'default' : 'ghost'}
            className="w-full justify-start"
            onClick={() => setActiveTab('conversations')}
          >
            <FileText className="mr-2 h-4 w-4" />
            Conversations
          </Button>
          
          <Button 
            variant={activeTab === 'cases' ? 'default' : 'ghost'}
            className="w-full justify-start"
            onClick={() => setActiveTab('cases')}
            disabled={state.editingCases.length === 0}
          >
            <Plus className="mr-2 h-4 w-4" />
            Edit Cases ({state.editingCases.length})
          </Button>
          
          <Button 
            variant={activeTab === 'preview' ? 'default' : 'ghost'}
            className="w-full justify-start"
            onClick={() => setActiveTab('preview')}
            disabled={state.editingCases.length === 0}
          >
            <Play className="mr-2 h-4 w-4" />
            Preview Results
          </Button>
          
          <Button 
            variant={activeTab === 'datasets' ? 'default' : 'ghost'}
            className="w-full justify-start"
            onClick={() => setActiveTab('datasets')}
          >
            <FolderOpen className="mr-2 h-4 w-4" />
            Datasets ({datasets.length})
          </Button>
        </div>
        
        <Separator className="my-4" />
        
        {/* Quick Actions */}
        <div className="p-4 space-y-2">
          <Button 
            className="w-full"
            variant="outline"
            onClick={() => handleSaveToDataset()}
            disabled={state.editingCases.length === 0}
          >
            <Save className="mr-2 h-4 w-4" />
            Save to Dataset
          </Button>
          
          <Button 
            className="w-full"
            variant="outline"
            onClick={handlePreviewRun}
            disabled={state.editingCases.length === 0}
          >
            <Play className="mr-2 h-4 w-4" />
            Run Preview
          </Button>
        </div>
        
        {/* Status */}
        {state.selectedConversation && (
          <div className="p-4 border-t">
            <div className="text-sm space-y-1">
              <div className="font-medium">Selected Conversation</div>
              <div className="text-muted-foreground text-xs">
                {state.selectedConversation.id}
              </div>
              <div className="flex gap-1 mt-2">
                <Badge variant="outline" className="text-xs">
                  {state.selectedConversation.workflow}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {state.selectedConversation.message_count} messages
                </Badge>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="p-6">
            {activeTab === 'conversations' && (
              <ConversationList 
                conversations={conversations}
                onSelect={handleConversationSelect}
                selectedId={state.selectedConversation?.id}
              />
            )}
            
            {activeTab === 'cases' && (
              <EvalCaseEditor
                cases={state.editingCases}
                onCaseUpdate={handleCaseUpdate}
                conversation={state.selectedConversation}
              />
            )}
            
            {activeTab === 'preview' && (
              <EvalPreview
                cases={state.editingCases}
                results={state.previewResults}
                onRerun={handlePreviewRun}
              />
            )}
            
            {activeTab === 'datasets' && (
              <DatasetManager
                datasets={datasets}
                onRefresh={loadDatasets}
                currentCases={state.editingCases}
                onSaveCases={handleSaveToDataset}
              />
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}