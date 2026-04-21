import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: '100vh', background: '#020617', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
          <div style={{ width: '100%', maxWidth: 640, border: '1px solid rgba(255,255,255,0.15)', borderRadius: 20, padding: 32, textAlign: 'center' }}>
            <h1 style={{ margin: 0, marginBottom: 8, fontWeight: 900, fontSize: 36 }}>System Error</h1>
            <p style={{ margin: 0, marginBottom: 20, opacity: 0.8 }}>Something crashed</p>
            <p style={{ margin: 0, marginBottom: 24, background: 'rgba(255,255,255,0.05)', padding: 12, borderRadius: 10 }}>
              {this.state.error?.message || "Unknown error"}
            </p>
            <button
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/'; }}
              style={{
                background: '#2563eb', color: '#fff', border: 'none',
                padding: '12px 32px', borderRadius: 12, fontWeight: 900,
                cursor: 'pointer', fontSize: 12, letterSpacing: 2, textTransform: 'uppercase'
              }}
            >
              Return to Home
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
