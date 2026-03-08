import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router-dom";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
          <div className="w-16 h-16 mb-4 rounded-full bg-[var(--color-accent-crimson)]/20 border border-[var(--color-accent-crimson)]/30 flex items-center justify-center">
            <svg className="w-8 h-8 text-[var(--color-accent-crimson)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="font-heading text-xl text-[var(--color-text-heading)] mb-2">
            The path ahead is shrouded in darkness...
          </h2>
          <p className="text-sm text-[var(--color-text-secondary)] mb-1">
            Something went wrong rendering this page.
          </p>
          <p className="text-xs text-[var(--color-text-muted)] mb-6 max-w-md">
            {this.state.error?.message}
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => this.setState({ hasError: false, error: null })}
              className="poe-btn-primary text-sm"
            >
              Try Again
            </button>
            <Link to="/" className="poe-btn-secondary text-sm">
              Return Home
            </Link>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
