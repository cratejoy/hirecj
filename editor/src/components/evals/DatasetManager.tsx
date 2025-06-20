import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { EvalDataset, EvalCase } from '@/types/evals';
import { FolderOpen, Download, Upload, Plus, RefreshCw, FileText, Save } from 'lucide-react';

interface DatasetManagerProps {
  datasets: EvalDataset[];
  onRefresh: () => void;
  currentCases?: EvalCase[];
  onSaveCases?: (datasetId: string) => void;
}

export function DatasetManager({ datasets, onRefresh, currentCases, onSaveCases }: DatasetManagerProps) {
  const [selectedDataset, setSelectedDataset] = useState<EvalDataset | null>(null);
  const [showNewDatasetForm, setShowNewDatasetForm] = useState(false);
  const [newDataset, setNewDataset] = useState({
    name: '',
    description: '',
    category: 'generated' as const,
  });

  const handleCreateDataset = async () => {
    if (!newDataset.name.trim()) return;

    try {
      const response = await fetch('/api/v1/evals/datasets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newDataset,
          cases: currentCases || [],
        }),
      });

      if (response.ok) {
        setShowNewDatasetForm(false);
        setNewDataset({ name: '', description: '', category: 'generated' });
        onRefresh();
      }
    } catch (error) {
      console.error('Failed to create dataset:', error);
    }
  };

  const handleExportDataset = async (dataset: EvalDataset) => {
    try {
      const response = await fetch(`/api/v1/evals/datasets/${dataset.id}/export`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${dataset.id}.jsonl`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Failed to export dataset:', error);
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'golden': return 'bg-yellow-500/10 text-yellow-700';
      case 'generated': return 'bg-blue-500/10 text-blue-700';
      case 'regression': return 'bg-red-500/10 text-red-700';
      default: return '';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold mb-2">Eval Datasets</h2>
          <p className="text-muted-foreground">
            Manage collections of eval test cases
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onRefresh}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button onClick={() => setShowNewDatasetForm(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Dataset
          </Button>
        </div>
      </div>

      {/* Current Cases Actions */}
      {currentCases && currentCases.length > 0 && (
        <Card className="border-primary/50">
          <CardHeader>
            <CardTitle className="text-base">Current Editing Session</CardTitle>
            <CardDescription>
              You have {currentCases.length} unsaved cases
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Select onValueChange={(value) => onSaveCases?.(value)}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select dataset..." />
                </SelectTrigger>
                <SelectContent>
                  {datasets.map(dataset => (
                    <SelectItem key={dataset.id} value={dataset.id}>
                      {dataset.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button 
                variant="default"
                onClick={() => setShowNewDatasetForm(true)}
              >
                <Save className="mr-2 h-4 w-4" />
                Save to New Dataset
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* New Dataset Form */}
      {showNewDatasetForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Create New Dataset</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Name</Label>
              <Input
                value={newDataset.name}
                onChange={(e) => setNewDataset({ ...newDataset, name: e.target.value })}
                placeholder="e.g., tool_selection_golden"
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={newDataset.description}
                onChange={(e) => setNewDataset({ ...newDataset, description: e.target.value })}
                placeholder="Describe the purpose of this dataset..."
              />
            </div>
            <div>
              <Label>Category</Label>
              <Select 
                value={newDataset.category} 
                onValueChange={(value: 'golden' | 'generated' | 'regression') => 
                  setNewDataset({ ...newDataset, category: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="golden">Golden (Manually Curated)</SelectItem>
                  <SelectItem value="generated">Generated (From Conversations)</SelectItem>
                  <SelectItem value="regression">Regression (Bug Fixes)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleCreateDataset}>Create Dataset</Button>
              <Button variant="outline" onClick={() => setShowNewDatasetForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Dataset List */}
      <div className="grid gap-4 md:grid-cols-2">
        {datasets.map(dataset => (
          <Card 
            key={dataset.id}
            className={`cursor-pointer transition-colors hover:bg-accent/50 ${
              selectedDataset?.id === dataset.id ? 'ring-2 ring-primary' : ''
            }`}
            onClick={() => setSelectedDataset(dataset)}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-base">{dataset.name}</CardTitle>
                  <CardDescription className="text-xs">
                    {dataset.description}
                  </CardDescription>
                </div>
                <Badge className={getCategoryColor(dataset.category)}>
                  {dataset.category}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <FileText className="h-4 w-4" />
                  {dataset.cases.length} cases
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleExportDataset(dataset);
                    }}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {dataset.metadata.tags && dataset.metadata.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {dataset.metadata.tags.map((tag, i) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {datasets.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <FolderOpen className="h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-muted-foreground">
              No datasets found
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Create a dataset to save your eval cases
            </p>
          </CardContent>
        </Card>
      )}

      {/* Selected Dataset Details */}
      {selectedDataset && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Dataset Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <Label className="text-sm">ID</Label>
                <p className="text-sm text-muted-foreground">{selectedDataset.id}</p>
              </div>
              <div>
                <Label className="text-sm">Version</Label>
                <p className="text-sm text-muted-foreground">{selectedDataset.metadata.version}</p>
              </div>
              <div>
                <Label className="text-sm">Created</Label>
                <p className="text-sm text-muted-foreground">
                  {new Date(selectedDataset.metadata.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <Label className="text-sm">Last Updated</Label>
                <p className="text-sm text-muted-foreground">
                  {new Date(selectedDataset.metadata.updated_at).toLocaleString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}