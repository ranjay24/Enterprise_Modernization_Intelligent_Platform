import React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';
import type { ProjectMetadata } from '@/types/upload';

interface ProjectFormProps {
  value: ProjectMetadata;
  onChange: (meta: ProjectMetadata) => void;
  disabled?: boolean;
}

const domains = ['E-Commerce', 'Healthcare', 'Finance', 'Insurance', 'Manufacturing', 'Retail', 'Education', 'Other'];
const environments: { value: ProjectMetadata['environment']; label: string }[] = [
  { value: 'development', label: 'Development' },
  { value: 'testing', label: 'Testing' },
  { value: 'production', label: 'Production' },
];

function InputField({ label, value, onChange, placeholder, required, disabled }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; required?: boolean; disabled?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-1.5">
        {label} {required && <span className="text-destructive">*</span>}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
      />
    </div>
  );
}

export function ProjectForm({ value, onChange, disabled }: ProjectFormProps) {
  const update = (patch: Partial<ProjectMetadata>) => onChange({ ...value, ...patch });

  return (
    <div className="w-full max-w-2xl mx-auto">
      <h3 className="text-sm font-semibold text-foreground mb-4">Project Details</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <InputField
          label="Project Name"
          value={value.projectName}
          onChange={(v) => update({ projectName: v })}
          placeholder="My Application"
          required
          disabled={disabled}
        />
        <InputField
          label="Application Version"
          value={value.version}
          onChange={(v) => update({ version: v })}
          placeholder="1.0.0"
          disabled={disabled}
        />
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-foreground mb-1.5">Description</label>
          <textarea
            value={value.description}
            onChange={(e) => update({ description: e.target.value })}
            placeholder="Brief description of the application..."
            rows={2}
            disabled={disabled}
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 resize-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">Business Domain</label>
          <div className="relative">
            <select
              value={value.businessDomain}
              onChange={(e) => update({ businessDomain: e.target.value })}
              disabled={disabled}
              className="w-full appearance-none rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 pr-8"
            >
              <option value="">Select domain</option>
              {domains.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          </div>
        </div>
        <InputField
          label="Team Name"
          value={value.teamName}
          onChange={(v) => update({ teamName: v })}
          placeholder="Platform Team"
          disabled={disabled}
        />
        <InputField
          label="Owner"
          value={value.owner}
          onChange={(v) => update({ owner: v })}
          placeholder="john.doe@company.com"
          disabled={disabled}
        />
        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">Environment</label>
          <div className="flex gap-2">
            {environments.map((env) => (
              <button
                key={env.value}
                type="button"
                disabled={disabled}
                onClick={() => update({ environment: env.value })}
                className={cn(
                  'flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
                  value.environment === env.value
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-muted text-muted-foreground hover:bg-accent'
                )}
              >
                {env.label}
              </button>
            ))}
          </div>
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-foreground mb-1.5">Tags</label>
          <input
            type="text"
            value={value.tags.join(', ')}
            onChange={(e) => update({ tags: e.target.value.split(',').map((t) => t.trim()).filter(Boolean) })}
            placeholder="microservices, spring-boot, aws (comma separated)"
            disabled={disabled}
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          />
        </div>
      </div>
    </div>
  );
}
