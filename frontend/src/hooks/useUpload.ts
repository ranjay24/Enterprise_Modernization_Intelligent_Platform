import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadCodebase, startAnalysis } from '@/services/jobService';

export function useUpload() {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(
    async (file: File) => {
      setUploading(true);
      setError(null);
      try {
        const job = await uploadCodebase(file);
        await startAnalysis(job.job_id);
        navigate(`/jobs/${job.job_id}`);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Upload failed';
        setError(message);
      } finally {
        setUploading(false);
      }
    },
    [navigate]
  );

  return { upload, uploading, error };
}
