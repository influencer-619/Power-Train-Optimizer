import { Navigate, Route, Routes } from "react-router-dom";
import StartPage from "./pages/StartPage";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";

/**
 * React + Vite + Tailwind source tree.
 * The packaged EXE currently serves `frontend/dist` (static SPA) so the app
 * runs without Node. When Node/npm are available, `npm run build` rebuilds dist.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<StartPage />} />
      <Route path="/app/:projectId" element={<AppLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}
