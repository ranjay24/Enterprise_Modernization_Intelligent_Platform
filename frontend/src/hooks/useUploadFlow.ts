import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadCodebase, startAnalysis } from '@/services/jobService';
import type { ProjectMetadata, UploadProgressData, UploadValidation, UploadSuccessData } from '@/types/upload';
import { defaultValidations } from '@/data/mockUploadData';

export type FlowStep = 'form' | 'validating' | 'uploading' | 'processing' | 'success' | 'error';

export function useUploadFlow() {
  const navigate = useNavigate();
  const [step, setStep] = useState<FlowStep>('form');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState<ProjectMetadata>({
    projectName: '',
    version: '',
    description: '',
    businessDomain: '',
    teamName: '',
    owner: '',
    tags: [],
    environment: 'development',
  });
  const [validations, setValidations] = useState<UploadValidation[]>(defaultValidations);
  const [progress, setProgress] = useState<UploadProgressData>({
    stage: 'idle', progress: 0, uploadedBytes: 0, totalBytes: 0,
    speed: 0, estimatedRemaining: 0, fileName: '', jobId: null, error: null,
  });
  const [successData, setSuccessData] = useState<UploadSuccessData | null>(null);
  const [errorType, setErrorType] = useState<'invalid_zip' | 'upload_failed' | 'network_error' | 'backend_unavailable' | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const startTimeRef = useRef<number>(0);
  const abortRef = useRef<boolean>(false);

  const runValidation = useCallback(async (file: File) => {
    setStep('validating');
    const updated = [...defaultValidations];

    for (let i = 0; i < updated.length; i++) {
      await new Promise((r) => setTimeout(r, 120 + Math.random() * 80));
      if (i < 4) {
        updated[i] = { ...updated[i], status: 'pass' };
      } else {
        updated[i] = { ...updated[i], status: file.size <= 500 * 1024 * 1024 ? 'pass' : 'fail' };
      }
      setValidations([...updated]);
    }

    const hasFailure = updated.some((v) => v.status === 'fail');
    if (hasFailure) {
      setErrorType('invalid_zip');
      setStep('error');
      return false;
    }
    return true;
  }, []);

  const handleFileSelect = useCallback(async (file: File) => {
    setSelectedFile(file);
    setMetadata((prev) => ({
      ...prev,
      projectName: prev.projectName || file.name.replace(/\.zip$/i, '').replace(/[-_]/g, ' '),
    }));
    const valid = await runValidation(file);
    if (!valid) return;
    setStep('form');
  }, [runValidation]);

  const startUpload = useCallback(async () => {
    if (!selectedFile) return;
    setStep('uploading');
    startTimeRef.current = Date.now();
    abortRef.current = false;

    setProgress({
      stage: 'uploading', progress: 0, uploadedBytes: 0,
      totalBytes: selectedFile.size, speed: 0, estimatedRemaining: 0,
      fileName: selectedFile.name, jobId: null, error: null,
    });

    // Simulate upload progress — completes in ~3 seconds
    const interval = setInterval(() => {
      if (abortRef.current) { clearInterval(interval); return; }
      setProgress((prev) => {
        const elapsed = (Date.now() - startTimeRef.current) / 1000;
        const uploaded = Math.min(prev.totalBytes * Math.min(elapsed / 3, 1), prev.totalBytes);
        const pct = (uploaded / prev.totalBytes) * 100;
        const speed = elapsed > 0 ? uploaded / elapsed : 0;
        const remaining = speed > 0 ? (prev.totalBytes - uploaded) / speed : 0;
        return { ...prev, uploadedBytes: uploaded, progress: pct, speed, estimatedRemaining: remaining };
      });
    }, 150);

    try {
      const job = await uploadCodebase(selectedFile);
      if (abortRef.current) { clearInterval(interval); return; }
      clearInterval(interval);

      setProgress((prev) => ({ ...prev, stage: 'processing', progress: 100, uploadedBytes: prev.totalBytes, speed: 0, estimatedRemaining: 0 }));

      await startAnalysis(job.job_id);

      const uploadTime = ((Date.now() - startTimeRef.current) / 1000).toFixed(1);
      setSuccessData({
        projectName: metadata.projectName || selectedFile.name,
        fileSize: selectedFile.size,
        jobId: job.job_id,
        uploadTime: parseFloat(uploadTime),
      });
      setStep('success');
    } catch (err: unknown) {
      clearInterval(interval);
      if (abortRef.current) return;
      const msg = err instanceof Error ? err.message : 'Upload failed';
      if (msg.includes('network') || msg.includes('Network')) {
        setErrorType('network_error');
      } else if (msg.includes('503') || msg.includes('unavailable')) {
        setErrorType('backend_unavailable');
      } else {
        setErrorType('upload_failed');
      }
      setErrorMessage(msg);
      setStep('error');
    }
  }, [selectedFile, metadata]);

  const cancelUpload = useCallback(() => {
    abortRef.current = true;
    setStep('form');
    setProgress({
      stage: 'idle', progress: 0, uploadedBytes: 0, totalBytes: 0,
      speed: 0, estimatedRemaining: 0, fileName: '', jobId: null, error: null,
    });
  }, []);

  const retry = useCallback(() => {
    setStep('form');
    setErrorType(null);
    setErrorMessage(null);
    setValidations(defaultValidations);
    setProgress({
      stage: 'idle', progress: 0, uploadedBytes: 0, totalBytes: 0,
      speed: 0, estimatedRemaining: 0, fileName: '', jobId: null, error: null,
    });
  }, []);

  const reset = useCallback(() => {
    setStep('form');
    setSelectedFile(null);
    setMetadata({
      projectName: '', version: '', description: '', businessDomain: '',
      teamName: '', owner: '', tags: [], environment: 'development',
    });
    setValidations(defaultValidations);
    setErrorType(null);
    setErrorMessage(null);
    setSuccessData(null);
    setProgress({
      stage: 'idle', progress: 0, uploadedBytes: 0, totalBytes: 0,
      speed: 0, estimatedRemaining: 0, fileName: '', jobId: null, error: null,
    });
  }, []);

  return {
    step, selectedFile, metadata, setMetadata, validations,
    progress, successData, errorType, errorMessage,
    handleFileSelect, startUpload, cancelUpload, retry, reset, navigate,
  };
}
