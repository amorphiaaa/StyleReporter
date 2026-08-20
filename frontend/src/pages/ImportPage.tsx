export function ImportPage() {
  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Future workflow</p>
          <h2>Questionnaire imports</h2>
        </div>
        <span className="muted-label">Google Sheets adapter pending</span>
      </div>
      <div className="empty-card">
        <div className="empty-icon" aria-hidden="true">
          +
        </div>
        <h3>Import screen placeholder</h3>
        <p>
          The future screen will start a manual Google Sheets sync and show import
          run results. No provider calls are made by this scaffold.
        </p>
      </div>
    </section>
  );
}
