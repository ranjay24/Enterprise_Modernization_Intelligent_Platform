import { useMemo, useState } from 'react';
import { File, Folder, ChevronRight, ChevronDown, Copy, Check } from 'lucide-react';
import type { ServiceCode, CodeGenFile } from '@/types';
import { cn } from '@/utils/cn';

interface TreeFile {
  name: string;
  path: string;
  content: string;
}

interface TreeNode {
  name: string;
  children?: TreeNode[];
  file?: TreeFile;
}

function buildTree(files: CodeGenFile[]): TreeNode {
  const root: TreeNode = { name: '.', children: [] };
  const sorted = [...files].sort((a, b) => a.path.localeCompare(b.path));
  for (const f of sorted) {
    const parts = f.path.split('/');
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      let child = node.children?.find((c) => c.name === part && !c.file);
      if (!child) {
        child = { name: part, children: [] };
        node.children!.push(child);
      }
      node = child;
    }
    const name = parts[parts.length - 1];
    node.children!.push({ name, file: { name, path: f.path, content: f.content } });
  }
  return root;
}

interface CodeExplorerProps {
  code: ServiceCode;
  onOpenFile?: (path: string) => void;
  height?: string;
}

export function CodeExplorer({ code, onOpenFile, height = 'h-[70vh]' }: CodeExplorerProps) {
  const [openDirs, setOpenDirs] = useState<Set<string>>(new Set(['.']));
  const [selected, setSelected] = useState<TreeFile | null>(null);
  const [copied, setCopied] = useState(false);

  const tree = useMemo(() => buildTree(code.files || []), [code.files]);

  const toggleDir = (name: string) => {
    setOpenDirs((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const selectFile = (file: TreeFile) => {
    setSelected(file);
    setCopied(false);
    if (onOpenFile) onOpenFile(file.path);
  };

  const copyFile = async () => {
    if (!selected) return;
    try {
      await navigator.clipboard.writeText(selected.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable
    }
  };

  const renderNode = (node: TreeNode, depth: number): React.ReactNode => {
    if (node.file) {
      const isSelected = selected?.path === node.file.path;
      return (
        <button
          key={node.file.path}
          onClick={() => selectFile(node.file!)}
          className={cn(
            'flex items-center gap-1.5 w-full rounded-md px-2 py-1 text-left text-xs transition-colors',
            isSelected ? 'bg-[var(--accent-blue)]/10 text-[var(--accent-blue)]' : 'text-[var(--text-muted)] hover:bg-[var(--border-subtle)] hover:text-[var(--text-primary)]'
          )}
          style={{ paddingLeft: 8 + depth * 14 }}
        >
          <File className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{node.file.name}</span>
        </button>
      );
    }
    const isOpen = openDirs.has(node.name);
    return (
      <div key={node.name}>
        <button
          onClick={() => toggleDir(node.name)}
          className="flex items-center gap-1.5 w-full rounded-md px-2 py-1 text-left text-xs text-[var(--text-primary)] hover:bg-[var(--border-subtle)] transition-colors"
          style={{ paddingLeft: 8 + depth * 14 }}
        >
          {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)]" /> : <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />}
          <Folder className="w-3.5 h-3.5 text-[var(--accent-blue)]/70" />
          <span className="truncate">{node.name}</span>
        </button>
        {isOpen && node.children?.map((c) => renderNode(c, depth + 1))}
      </div>
    );
  };

  return (
    <div className={cn('rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden', height)}>
      <div className="grid grid-cols-2 h-full min-h-0">
        <div className="border-r border-[var(--border-subtle)] overflow-y-auto min-h-0 p-2">
          {code.files && code.files.length > 0 ? (
            renderNode(tree, 0)
          ) : (
            <p className="text-xs text-[var(--text-muted)] p-3">No files generated yet.</p>
          )}
        </div>
        <div className="flex flex-col min-w-0 min-h-0">
          <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-subtle)] bg-[var(--bg-elevated)]/50 shrink-0">
            <span className="text-[11px] text-[var(--text-muted)] truncate">
              {selected ? selected.path : 'Select a file to view'}
            </span>
            {selected && (
              <button
                onClick={copyFile}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors shrink-0"
                title="Copy file content"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-[var(--success)]" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            )}
          </div>
          <div className="flex-1 overflow-auto min-h-0">
            {selected ? (
              <pre className="p-3 text-[11px] leading-relaxed text-[var(--text-primary)] whitespace-pre font-mono">
                <code>{selected.content}</code>
              </pre>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-[var(--text-muted)]">
                <File className="w-8 h-8 mb-2 opacity-40" />
                <p className="text-xs">No file selected</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
