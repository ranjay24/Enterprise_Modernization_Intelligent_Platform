import { useMemo } from 'react';
import { useAnalysisResults } from '@/hooks/useAnalysisResults';
import { useAppStore } from '@/store/useAppStore';
import { mockResultsData } from '@/data/mockResults';
import {
  computeConfidenceBreakdown,
  computeRiskHeatmap,
  computeRecommendations,
  computeValidation,
  computeArtifacts,
  computeExports,
} from '@/types/results';
import type { ResultsData } from '@/types/results';

export function useResultsData(jobId: string | undefined) {
  const demoMode = useAppStore((s) => s.demoMode);
  const apiQuery = useAnalysisResults(demoMode ? undefined : jobId);

  const data: ResultsData | null = useMemo(() => {
    if (demoMode) return mockResultsData;
    if (!apiQuery.data) return null;
    const analysis = apiQuery.data;
    return {
      analysis,
      confidence: computeConfidenceBreakdown(analysis),
      riskHeatmap: computeRiskHeatmap(analysis.service_boundaries),
      recommendations: computeRecommendations(analysis),
      validation: computeValidation(analysis),
      artifacts: computeArtifacts(analysis),
      exports: computeExports(),
    };
  }, [demoMode, apiQuery.data]);

  return {
    data,
    isLoading: demoMode ? false : apiQuery.isLoading,
    isError: demoMode ? false : apiQuery.isError,
    error: apiQuery.error,
    demoMode,
  };
}
