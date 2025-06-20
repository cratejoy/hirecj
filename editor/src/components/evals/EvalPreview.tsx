import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { EvalCase, EvalPreviewResult } from '@/types/evals';
import { Play, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface EvalPreviewProps {
  cases: EvalCase[];
  results?: EvalPreviewResult[];
  onRerun: () => void;
}

export function EvalPreview({ cases, results, onRerun }: EvalPreviewProps) {
  const passedCount = results?.filter(r => r.passed).length || 0;
  const totalCount = results?.length || 0;
  const passRate = totalCount > 0 ? (passedCount / totalCount) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold mb-2">Preview Results</h2>
          <p className="text-muted-foreground">
            Test your eval cases against the current agent configuration
          </p>
        </div>
        <Button onClick={onRerun}>
          <Play className="mr-2 h-4 w-4" />
          Run Preview
        </Button>
      </div>

      {results && results.length > 0 && (
        <>
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Pass Rate</span>
                  <div className="flex items-center gap-2">
                    <Progress value={passRate} className="w-[100px]" />
                    <span className="text-sm font-medium">{passRate.toFixed(1)}%</span>
                  </div>
                </div>
                <div className="flex gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span>{passedCount} passed</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <XCircle className="h-4 w-4 text-red-600" />
                    <span>{totalCount - passedCount} failed</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Detailed Results */}
          <div className="space-y-4">
            {results.map((result, index) => {
              const evalCase = cases.find(c => c.id === result.case_id);
              if (!evalCase) return null;

              return (
                <Card key={result.case_id} className={result.passed ? '' : 'border-red-500/50'}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-base flex items-center gap-2">
                          Turn {evalCase.metadata.turn}
                          {result.passed ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-600" />
                          )}
                        </CardTitle>
                        <CardDescription className="text-xs">
                          {evalCase.sample_id}
                        </CardDescription>
                      </div>
                      <Badge variant={result.passed ? 'secondary' : 'destructive'}>
                        {result.passed ? 'PASS' : 'FAIL'}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {/* Tool Selection Results */}
                    {result.details.tool_selection && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium">Tool Selection</h4>
                        <div className="text-sm space-y-1">
                          <div className="flex items-start gap-2">
                            <span className="text-muted-foreground">Expected:</span>
                            <div className="flex flex-wrap gap-1">
                              {result.details.tool_selection.expected.map((tool, i) => (
                                <Badge key={i} variant="outline" className="text-xs">
                                  {tool}
                                </Badge>
                              ))}
                            </div>
                          </div>
                          <div className="flex items-start gap-2">
                            <span className="text-muted-foreground">Actual:</span>
                            <div className="flex flex-wrap gap-1">
                              {result.details.tool_selection.actual.map((tool, i) => (
                                <Badge 
                                  key={i} 
                                  variant={result.details.tool_selection!.expected.includes(tool) ? 'secondary' : 'destructive'} 
                                  className="text-xs"
                                >
                                  {tool}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Response Quality Results */}
                    {result.details.response_quality && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium">Response Quality</h4>
                        <div className="text-sm space-y-1">
                          {result.details.response_quality.criteria_met.length > 0 && (
                            <div className="flex items-start gap-2">
                              <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                              <div className="flex-1">
                                <span className="text-muted-foreground">Criteria met:</span>
                                <ul className="list-disc list-inside text-xs mt-1 text-muted-foreground">
                                  {result.details.response_quality.criteria_met.map((criteria, i) => (
                                    <li key={i}>{criteria}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}
                          {result.details.response_quality.criteria_missed.length > 0 && (
                            <div className="flex items-start gap-2">
                              <XCircle className="h-4 w-4 text-red-600 mt-0.5" />
                              <div className="flex-1">
                                <span className="text-muted-foreground">Criteria missed:</span>
                                <ul className="list-disc list-inside text-xs mt-1 text-muted-foreground">
                                  {result.details.response_quality.criteria_missed.map((criteria, i) => (
                                    <li key={i}>{criteria}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Errors */}
                    {result.details.errors && result.details.errors.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium flex items-center gap-1">
                          <AlertCircle className="h-4 w-4 text-amber-600" />
                          Errors
                        </h4>
                        <ul className="list-disc list-inside text-xs text-muted-foreground">
                          {result.details.errors.map((error, i) => (
                            <li key={i}>{error}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Score */}
                    {result.score !== undefined && (
                      <div className="flex items-center justify-between pt-2 border-t">
                        <span className="text-sm font-medium">Score</span>
                        <Badge variant="outline">
                          {(result.score * 100).toFixed(1)}%
                        </Badge>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </>
      )}

      {(!results || results.length === 0) && cases.length > 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Play className="h-8 w-8 text-muted-foreground mb-3" />
            <p className="text-muted-foreground mb-4">
              Click "Run Preview" to test your eval cases
            </p>
            <Button onClick={onRerun}>
              <Play className="mr-2 h-4 w-4" />
              Run Preview
            </Button>
          </CardContent>
        </Card>
      )}

      {cases.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <p className="text-muted-foreground">
              No eval cases to preview. Create some cases first.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}