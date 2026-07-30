import React from 'react';
import { AlertCircle } from 'lucide-react';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <AlertCircle className="w-10 h-10 text-destructive mb-3" />
          <h3 className="font-semibold text-foreground mb-1">Something went wrong</h3>
          <p className="text-sm text-muted-foreground">{this.state.error?.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
