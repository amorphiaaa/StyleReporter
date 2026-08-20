import { NavLink, Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Style Language Method</p>
          <h1>StyleReporter</h1>
        </div>
        <span className="stage-badge">Scaffold</span>
      </header>
      <div className="workspace">
        <aside className="sidebar">
          <nav aria-label="Primary navigation">
            <NavLink to="/clients">Clients</NavLink>
            <NavLink to="/imports">Imports</NavLink>
          </nav>
        </aside>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
