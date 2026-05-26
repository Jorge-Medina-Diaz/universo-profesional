/**
 * Catches React render errors and shows a useful message instead of leaving
 * the user staring at a blank page. Supports a custom fallback UI and soft
 * retry (no full reload) when used as a per-route wrapper.
 */
import { Component, type ReactNode, type ErrorInfo } from "react";

interface Props {
  children: ReactNode;
  /** Optional contextual fallback rendered instead of the generic error card. */
  fallback?: ReactNode;
  /** Called when the boundary catches an error (e.g. log to Sentry). */
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface State {
  error: Error | null;
  info: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, info: null };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[react] Uncaught render error:", error, info);
    this.setState({ info });
    this.props.onError?.(error, info);
  }

  reset = () => {
    this.setState({ error: null, info: null });
  };

  render() {
    if (this.state.error) {
      if (this.props.fallback != null) {
        return this.props.fallback;
      }
      return (
        <div className="max-w-2xl mx-auto py-12 px-4">
          <div className="rounded-lg border border-red-200 bg-red-50 p-5">
            <h1 className="text-lg font-bold text-red-800 mb-2">
              Algo ha petado en la UI
            </h1>
            <p className="text-sm text-red-700 mb-3">
              La página no pudo renderizarse. Esto NO afecta a tus datos —
              solo es un error en el frontend. Abajo tienes el detalle y un
              botón para reintentar.
            </p>
            <pre className="text-xs bg-white border border-red-200 rounded p-3 overflow-auto max-h-64 whitespace-pre-wrap">
              {this.state.error.message}
              {this.state.error.stack && "\n\n" + this.state.error.stack}
            </pre>
            <div className="mt-3 flex gap-2">
              <button onClick={this.reset} className="btn-primary">
                Reintentar
              </button>
              <a href="#/connections" className="btn-secondary">
                Ir a Conexiones
              </a>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
