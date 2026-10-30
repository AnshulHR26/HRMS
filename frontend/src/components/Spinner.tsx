export function Spinner({ size = 20, label }: { size?: number; label?: string }) {
  return (
    <span className="spinner-wrap" role="status" aria-live="polite">
      <span className="spinner" style={{ width: size, height: size }} />
      {label && <span className="spinner-label">{label}</span>}
    </span>
  );
}

export function FullPageSpinner() {
  return (
    <div className="full-page-center">
      <Spinner size={32} label="Loading…" />
    </div>
  );
}

export function SectionLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="section-loader">
      <Spinner size={24} label={label} />
    </div>
  );
}
