import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./layout/AppLayout";
import { ClientsPage } from "./pages/ClientsPage";
import { ImportPage } from "./pages/ImportPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/clients" replace />} />
          <Route path="/clients" element={<ClientsPage />} />
          <Route path="/imports" element={<ImportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
