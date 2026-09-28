import { usePaths } from "../contexts/PathsContext";
import { useAuth } from "./useAuth";
import { backendEnabled } from "../services/apiClient";
import { visibleToEmployee } from "../utils/pathWorkflow";

/**
 * Learning paths for current logged-in employee. When backend is enabled, server returns paths
 * assigned to this employee (enrollment records), so no client-side department/role re-filtering is needed.
 */
export function useMyPaths() {
  const { paths } = usePaths();
  const { user } = useAuth();
  if (backendEnabled()) return paths.filter(p => p.status === "published");
  return paths.filter(p => visibleToEmployee(p, user));
}
