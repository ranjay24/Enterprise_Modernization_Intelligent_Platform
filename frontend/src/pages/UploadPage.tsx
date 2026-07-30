import { useState, useRef } from 'react';
import { Upload, History, ArrowRight, Inbox, FileCheck, Clock, Target } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useUploadFlow } from '@/hooks/useUploadFlow';
import { UploadZone } from '@/components/upload/UploadZone';
import { UploadProgressCard } from '@/components/upload/UploadProgressCard';
import { ValidationCard } from '@/components/upload/ValidationCard';
import { FrameworkCard } from '@/components/upload/FrameworkCard';
import { ProjectForm } from '@/components/upload/ProjectForm';
import { HistoryTable } from '@/components/upload/HistoryTable';
import { WorkflowTimeline } from '@/components/upload/WorkflowTimeline';
import { SuccessDialog } from '@/components/upload/SuccessDialog';
import { ErrorBanner } from '@/components/upload/ErrorBanner';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { cn } from '@/utils/cn';
import { mockUploadHistory, mockSupportedFrameworks, mockWorkflowSteps } from '@/data/mockUploadData';
import { useAppStore } from '@/store/useAppStore';

const statItems = [
  { icon: Clock, label: 'Full Analysis', value: '< 5min', color: 'text-primary' },
  { icon: FileCheck, label: 'Dimensions Scored', value: '6', color: 'text-success' },
  { icon: Target, label: 'Accuracy Target', value: '90%+', color: 'text-info' },
];

export default function UploadPage() {
  const { demoMode } = useAppStore();
  const {
    step, selectedFile, metadata, setMetadata, validations,
    progress, successData, errorType, errorMessage,
    handleFileSelect, startUpload, cancelUpload, retry, reset,
  } = useUploadFlow();
  const [showHistory, setShowHistory] = useState(false);
  const uploadZoneRef = useRef<HTMLDivElement>(null);

  const workflowStep = step === 'uploading' || step === 'processing' ? 1
    : step === 'success' ? 5
    : undefined;

  const scrollToUpload = () => {
    uploadZoneRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-8">
      {/* ── Header ── */}
      <div className="text-center space-y-4">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/8 text-primary text-xs font-medium mb-2"
        >
          <Upload className="w-3.5 h-3.5" />
          Code Analysis
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-h1 text-foreground"
        >
          Start a Modernization Assessment
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-body text-muted-foreground max-w-lg mx-auto"
        >
          Upload your Java Spring Boot application to receive AI-powered modernization recommendations.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex items-center justify-center gap-3 pt-2"
        >
          {step === 'form' && !selectedFile ? (
            <Button onClick={scrollToUpload} size="lg" className="gap-2">
              <Upload className="w-4 h-4" />
              Upload Project
            </Button>
          ) : (
            <Button disabled size="lg"><Upload className="w-4 h-4 mr-1" />Upload Project</Button>
          )}
          <Button variant="outline" size="lg" onClick={() => setShowHistory(!showHistory)} className="gap-2">
            <History className="w-4 h-4" />
            {showHistory ? 'Hide History' : 'View Previous Analyses'}
          </Button>
        </motion.div>
      </div>

      {/* ── Error Banner ── */}
      <AnimatePresence>
        {step === 'error' && errorType && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <ErrorBanner type={errorType} message={errorMessage || undefined} onRetry={retry} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Upload Progress ── */}
      <AnimatePresence>
        {(step === 'uploading' || step === 'processing') && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <UploadProgressCard progress={progress} onCancel={cancelUpload} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Upload Zone ── */}
      <div ref={uploadZoneRef}>
        <AnimatePresence mode="wait">
          {step === 'form' && !selectedFile && (
            <motion.div
              key="upload-zone"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <UploadZone onFile={handleFileSelect} uploading={false} disabled={false} />
            </motion.div>
          )}
          {step === 'validating' && (
            <motion.div
              key="upload-zone-validating"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <UploadZone onFile={handleFileSelect} uploading={true} disabled={true} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Validation Cards ── */}
      <AnimatePresence>
        {step === 'validating' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <ValidationCard validations={validations} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Project Form + Upload Button ── */}
      <AnimatePresence>
        {step === 'form' && selectedFile && (
          <motion.div
            key="project-form"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-6"
          >
            <Card>
              <CardContent className="pt-6">
                <ProjectForm value={metadata} onChange={setMetadata} />
              </CardContent>
            </Card>
            <div className="flex justify-center">
              <Button size="xl" onClick={startUpload} className="gap-2">
                <Upload className="w-4 h-4" />
                Start Upload & Analysis
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Idle sections ── */}
      {step === 'form' && !selectedFile && (
        <div className="space-y-8">
          <WorkflowTimeline steps={mockWorkflowSteps} activeStep={workflowStep} />
          <FrameworkCard frameworks={mockSupportedFrameworks} />

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 max-w-2xl mx-auto">
            {statItems.map((item) => (
              <div key={item.label} className="rounded-xl border bg-card p-5 text-center hover:shadow-sm transition-all duration-fast">
                <item.icon className={cn('w-6 h-6 mx-auto mb-2', item.color)} />
                <div className={cn('text-xl font-bold', item.color)}>{item.value}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Upload History ── */}
      <AnimatePresence>
        {showHistory && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            {demoMode ? (
              <HistoryTable data={mockUploadHistory} />
            ) : (
              <div className="border rounded-xl bg-card p-12 text-center">
                <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center mx-auto mb-4">
                  <Inbox className="w-6 h-6 text-muted-foreground/60" />
                </div>
                <h4 className="font-semibold text-foreground mb-1">No previous analyses</h4>
                <p className="text-sm text-muted-foreground mb-4">Upload a project to get started</p>
                <Button variant="outline" size="sm" onClick={scrollToUpload} className="gap-2">
                  <Upload className="w-3.5 h-3.5" />
                  Upload First Project
                </Button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Success Dialog ── */}
      <AnimatePresence>
        {step === 'success' && successData && (
          <SuccessDialog data={successData} onDismiss={reset} />
        )}
      </AnimatePresence>
    </div>
  );
}
