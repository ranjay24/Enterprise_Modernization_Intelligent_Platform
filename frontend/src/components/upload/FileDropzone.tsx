import { useState, useRef } from 'react';
import { Upload, FileArchive, AlertCircle } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';

interface FileDropzoneProps {
  onFile: (file: File) => void;
  uploading?: boolean;
}

export function FileDropzone({ onFile, uploading }: FileDropzoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (file: File) => {
    if (!file.name.endsWith('.zip')) {
      setError('Only .zip files are supported');
      return false;
    }
    if (file.size > 500 * 1024 * 1024) {
      setError('File too large (max 500MB)');
      return false;
    }
    setError(null);
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

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all',
          dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50',
          uploading && 'pointer-events-none opacity-50'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".zip"
          onChange={handleChange}
          className="hidden"
          disabled={uploading}
        />
        {uploading ? (
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto animate-pulse">
              <Upload className="w-6 h-6 text-primary" />
            </div>
            <p className="font-medium text-foreground">Uploading...</p>
            <p className="text-sm text-muted-foreground">Please wait while we process your codebase</p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto">
              <FileArchive className="w-6 h-6 text-muted-foreground" />
            </div>
            <div>
              <p className="font-medium text-foreground">Drop your Java codebase here</p>
              <p className="text-sm text-muted-foreground">or click to browse &middot; .zip files up to 500MB</p>
            </div>
            <Button variant="outline" size="sm" disabled={uploading}>
              Choose File
            </Button>
          </div>
        )}
      </div>
      {error && (
        <div className="flex items-center gap-2 mt-3 text-sm text-destructive">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}
    </div>
  );
}
