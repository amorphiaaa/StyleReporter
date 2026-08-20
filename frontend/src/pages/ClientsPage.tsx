import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listClients } from "../api/client";
import type { ClientListItem } from "../types";

export function ClientsPage() {
  const [clients, setClients] = useState<ClientListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isCurrent = true;
    void listClients()
      .then((items) => {
        if (isCurrent) {
          setClients(items);
        }
      })
      .catch((requestError: unknown) => {
        if (isCurrent) {
          setError(requestError instanceof Error ? requestError.message : "Client list failed");
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Clients</h2>
        </div>
        <span className="muted-label">{clients.length} persisted profiles</span>
      </div>

      {isLoading ? <p className="loading-copy">Loading client records…</p> : null}
      {error ? <p className="notice error-notice">{error}</p> : null}

      {!isLoading && !error && clients.length === 0 ? (
        <div className="empty-card">
          <div className="empty-icon" aria-hidden="true">
            ◯
          </div>
          <h3>No clients yet</h3>
          <p>Run a manual import to create the first client profile.</p>
        </div>
      ) : null}

      {!isLoading && !error && clients.length > 0 ? (
        <div className="table-card">
          <table className="client-table">
            <thead>
              <tr>
                <th>Client</th>
                <th>Email</th>
                <th>Submissions</th>
                <th aria-label="Open client" />
              </tr>
            </thead>
            <tbody>
              {clients.map((client) => (
                <tr key={client.id}>
                  <td>
                    <strong>{client.display_name ?? "Unnamed client"}</strong>
                  </td>
                  <td className="secondary-cell">{client.email_normalized}</td>
                  <td>{client.submission_count}</td>
                  <td className="action-cell">
                    <Link className="text-link" to={`/clients/${client.id}`}>
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
