import { usePaths } from "../contexts/PathsContext";
import { useAuth } from "./useAuth";
import { visibleToEmployee } from "../utils/pathWorkflow";

/** Lộ trình đã phát hành cho phòng ban / vị trí của nhân viên đang đăng nhập */
export function useMyPaths() {
  const { paths } = usePaths();
  const { user } = useAuth();
  return paths.filter(p => visibleToEmployee(p, user));
}
