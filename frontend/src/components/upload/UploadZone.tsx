import React, { useState, useRef } from 'react';
import { Upload, FileArchive, AlertCircle, X, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';

interface UploadZoneProps {
  onFile: (file: File) => void;
  uploading?: boolean;
  disabled?: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function UploadZone({ onFile, uploading, disabled }: UploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (file: File): boolean => {
    if (!file.name.endsWith('.zip')) {
      setError('Only .zip files are supported');
      setSelectedFile(null);
      return false;
    }
    if (file.size > 500 * 1024 * 1024) {
      setError('File too large — maximum size is 500MB');
      setSelectedFile(null);
      return false;
    }
    setError(null);
    setSelectedFile(file);
    return true;
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && validate(file)) onFile(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && validate(file)) onFile(file);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const isDisabled = uploading || disabled;

  return (
    <div className="w-full max-w-2xl mx-auto">
      <input
        ref={inputRef}
        type="file"
        accept=".zip"
        onChange={handleChange}
        className="hidden"
        disabled={isDisabled}
        aria-label="Upload ZIP file"
      />
      <motion.div
        onDragOver={(e) => { e.preventDefault(); if (!isDisabled) setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !isDisabled && inputRef.current?.click()}
        whileHover={!isDisabled ? { scale: 1.005 } : undefined}
        whileTap={!isDisabled ? { scale: 0.995 } : undefined}
        className={cn(
          'relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-fast',
          dragOver && !isDisabled
            ? 'border-primary bg-primary/5 shadow-lg shadow-primary/5'
            : 'border-border hover:border-primary/50 hover:bg-accent/30',
          isDisabled && 'pointer-events-none opacity-60',
          error && 'border-danger/50 bg-danger-bg'
        )}
        role="button"
        tabIndex={0}
        aria-label="Drop zone for ZIP files"
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); !isDisabled && inputRef.current?.click(); } }}
      >
        <AnimatePresence mode="wait">
          {uploading ? (
            <motion.div
              key="uploading"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
              </div>
              <div>
                <p className="font-semibold text-foreground text-lg">Uploading your project...</p>
                <p className="text-sm text-muted-foreground mt-1">Please wait while we process your codebase</p>
              </div>
            </motion.div>
          ) : selectedFile ? (
            <motion.div
              key="selected"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              <div className="w-16 h-16 rounded-2xl bg-success-bg flex items-center justify-center mx-auto">
                <FileArchive className="w-8 h-8 text-success" />
              </div>
              <div>
                <p className="font-semibold text-foreground">{selectedFile.name}</p>
                <p className="text-sm text-muted-foreground mt-1">{formatBytes(selectedFile.size)}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={handleClear} className="gap-1.5 text-muted-foreground">
                <X className="w-4 h-4" />
                Remove
              </Button>
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              <motion.div
                className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mx-auto"
                animate={dragOver ? { scale: 1.1, backgroundColor: 'hsl(var(--primary) / 0.1)' } : { scale: 1 }}
              >
                {dragOver ? (
                  <Upload className="w-8 h-8 text-primary" />
                ) : (
                  <FileArchive className="w-8 h-8 text-muted-foreground" />
                )}
              </motion.div>
              <div>
                <p className="font-semibold text-foreground text-lg">
                  {dragOver ? 'Drop your file here' : 'Drop your Java codebase here'}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  or click to browse &middot; .zip files up to 500MB
                </p>
              </div>
              <Button variant="outline" size="sm" disabled={isDisabled} className="gap-1.5">
                <Upload className="w-4 h-4" />
                Choose File
              </Button>
              <div className="flex items-center justify-center gap-4 text-[11px] text-muted-foreground pt-2">
                <span className="flex items-center gap-1"><FileArchive className="w-3 h-3" /> ZIP only</span>
                <span className="text-border">|</span>
                <span>Max 500MB</span>
                <span className="text-border">|</span>
                <span>Spring Boot, Java, Maven, Gradle</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 mt-3 text-sm text-danger overflow-hidden"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
