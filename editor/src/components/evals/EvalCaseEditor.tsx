import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { EvalCase, ConversationSummary } from '@/types/evals';
import { Trash2, Plus, Edit2, Copy, Check, X } from 'lucide-react';

interface EvalCaseEditorProps {
  cases: EvalCase[];
  onCaseUpdate: (index: number, updatedCase: EvalCase) => void;
  conversation?: ConversationSummary;
}

export function EvalCaseEditor({ cases, onCaseUpdate, conversation }: EvalCaseEditorProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingCase, setEditingCase] = useState<EvalCase | null>(null);

  const startEditing = (index: number) => {
    setEditingIndex(index);
    setEditingCase(JSON.parse(JSON.stringify(cases[index]))); // Deep copy
  };

  const saveEditing = () => {
    if (editingIndex !== null && editingCase) {
      onCaseUpdate(editingIndex, editingCase);
      setEditingIndex(null);
      setEditingCase(null);
    }
  };

  const cancelEditing = () => {
    setEditingIndex(null);
    setEditingCase(null);
  };

  const updateIdealField = (path: string[], value: any) => {
    if (!editingCase) return;
    
    const newCase = { ...editingCase };
    let current: any = newCase.ideal;
    
    for (let i = 0; i < path.length - 1; i++) {
      if (!current[path[i]]) {
        current[path[i]] = {};
      }
      current = current[path[i]];
    }
    
    current[path[path.length - 1]] = value;
    setEditingCase(newCase);
  };

  const addToStringArray = (path: string[], value: string) => {
    if (!editingCase || !value.trim()) return;
    
    const newCase = { ...editingCase };
    let current: any = newCase.ideal;
    
    for (let i = 0; i < path.length - 1; i++) {
      if (!current[path[i]]) {
        current[path[i]] = {};
      }
      current = current[path[i]];
    }
    
    const fieldName = path[path.length - 1];
    if (!current[fieldName]) {
      current[fieldName] = [];
    }
    current[fieldName].push(value.trim());
    setEditingCase(newCase);
  };

  const removeFromStringArray = (path: string[], index: number) => {
    if (!editingCase) return;
    
    const newCase = { ...editingCase };
    let current: any = newCase.ideal;
    
    for (let i = 0; i < path.length - 1; i++) {
      current = current[path[i]];
    }
    
    const fieldName = path[path.length - 1];
    current[fieldName].splice(index, 1);
    setEditingCase(newCase);
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold mb-2">Edit Eval Cases</h2>
        <p className="text-muted-foreground">
          Define expected behavior for each turn in the conversation
        </p>
      </div>

      {conversation && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Source Conversation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{conversation.id}</Badge>
              <Badge variant="secondary">{conversation.workflow}</Badge>
              <span className="text-sm text-muted-foreground">
                {conversation.message_count} messages
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {cases.map((evalCase, index) => {
          const isEditing = editingIndex === index;
          const displayCase = isEditing ? editingCase! : evalCase;
          
          return (
            <Card key={evalCase.id} className={isEditing ? 'ring-2 ring-primary' : ''}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-base">
                      Turn {evalCase.metadata.turn}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      {evalCase.sample_id}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {!isEditing ? (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => startEditing(index)}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const newCase = JSON.parse(JSON.stringify(evalCase));
                            newCase.id = `${evalCase.id}_copy`;
                            newCase.sample_id = `${evalCase.sample_id}_copy`;
                            onCaseUpdate(cases.length, newCase);
                          }}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={saveEditing}
                        >
                          <Check className="h-4 w-4 text-green-600" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={cancelEditing}
                        >
                          <X className="h-4 w-4 text-red-600" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
                {/* User Input */}
                <div>
                  <Label className="text-sm font-medium">User Input</Label>
                  <div className="mt-1 p-3 bg-muted rounded-md text-sm">
                    {evalCase.input.messages[evalCase.input.messages.length - 1]?.content || 'No user input'}
                  </div>
                </div>

                {/* Actual Response (for reference) */}
                {evalCase.actual && (
                  <div>
                    <Label className="text-sm font-medium">Actual Response</Label>
                    <div className="mt-1 p-3 bg-muted rounded-md text-sm">
                      {evalCase.actual.response}
                    </div>
                    {evalCase.actual.tool_calls && evalCase.actual.tool_calls.length > 0 && (
                      <div className="mt-2 flex gap-1">
                        {evalCase.actual.tool_calls.map((tool, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {tool}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <Separator />

                {/* Expected Behavior */}
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold">Expected Behavior</h4>
                  
                  {/* Tool Selection */}
                  <div className="space-y-2">
                    <Label className="text-sm">Tool Selection</Label>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        checked={displayCase.ideal.tool_selection?.should_use_tool || false}
                        disabled={!isEditing}
                        onCheckedChange={(checked) => 
                          updateIdealField(['tool_selection', 'should_use_tool'], checked)
                        }
                      />
                      <label className="text-sm">Should use tools</label>
                    </div>
                    
                    {displayCase.ideal.tool_selection?.should_use_tool && (
                      <div className="ml-6 space-y-2">
                        <div>
                          <Label className="text-xs">Acceptable Tools</Label>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {displayCase.ideal.tool_selection?.acceptable_tools?.map((tool, i) => (
                              <Badge key={i} variant="secondary" className="text-xs">
                                {tool}
                                {isEditing && (
                                  <button
                                    className="ml-1"
                                    onClick={() => removeFromStringArray(['tool_selection', 'acceptable_tools'], i)}
                                  >
                                    <X className="h-3 w-3" />
                                  </button>
                                )}
                              </Badge>
                            ))}
                            {isEditing && (
                              <Input
                                className="h-6 w-32 text-xs"
                                placeholder="Add tool..."
                                onKeyPress={(e) => {
                                  if (e.key === 'Enter') {
                                    addToStringArray(['tool_selection', 'acceptable_tools'], (e.target as HTMLInputElement).value);
                                    (e.target as HTMLInputElement).value = '';
                                  }
                                }}
                              />
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Requirements (Plain English) */}
                  <div className="space-y-2">
                    <Label className="text-sm">Requirements</Label>
                    <p className="text-xs text-muted-foreground">
                      Describe in plain English what should be true about the response
                    </p>
                    
                    <div className="space-y-2">
                      {displayCase.ideal.requirements?.map((req, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <Badge variant="secondary" className="h-6 w-6 flex items-center justify-center p-0">
                            {i + 1}
                          </Badge>
                          <div className="flex-1">
                            {isEditing ? (
                              <Input
                                className="text-sm"
                                value={req}
                                onChange={(e) => {
                                  const newCase = { ...editingCase! };
                                  if (!newCase.ideal.requirements) {
                                    newCase.ideal.requirements = [];
                                  }
                                  newCase.ideal.requirements[i] = e.target.value;
                                  setEditingCase(newCase);
                                }}
                                placeholder="e.g., Must greet the user professionally"
                              />
                            ) : (
                              <p className="text-sm">{req}</p>
                            )}
                          </div>
                          {isEditing && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeFromStringArray(['requirements'], i)}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      ))}
                      
                      {isEditing && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => addToStringArray(['requirements'], '')}
                          className="w-full"
                        >
                          <Plus className="h-3 w-3 mr-1" />
                          Add Requirement
                        </Button>
                      )}
                      
                      {(!displayCase.ideal.requirements || displayCase.ideal.requirements.length === 0) && !isEditing && (
                        <p className="text-sm text-muted-foreground italic">
                          No requirements defined. Edit to add requirements.
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Notes */}
                  {isEditing && (
                    <div>
                      <Label className="text-sm">Notes</Label>
                      <Textarea
                        className="mt-1"
                        placeholder="Add notes about this test case..."
                        value={editingCase?.metadata.notes || ''}
                        onChange={(e) => {
                          const newCase = { ...editingCase! };
                          newCase.metadata.notes = e.target.value;
                          setEditingCase(newCase);
                        }}
                      />
                    </div>
                  )}
                  
                  {!isEditing && displayCase.metadata.notes && (
                    <div>
                      <Label className="text-sm">Notes</Label>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {displayCase.metadata.notes}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
      
      {cases.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <p className="text-muted-foreground">
              No eval cases loaded. Select a conversation to get started.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}