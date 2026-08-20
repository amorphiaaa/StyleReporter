export function ClientsPage() {
  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Clients</h2>
        </div>
        <span className="muted-label">Persistence is not connected</span>
      </div>
      <div className="empty-card">
        <div className="empty-icon" aria-hidden="true">
          ○
        </div>
        <h3>No clients yet</h3>
        <p>
          This page is a frontend shell. Client records will appear here after the
          questionnaire import workflow is implemented.
        </p>
      </div>
    </section>
  );
}
