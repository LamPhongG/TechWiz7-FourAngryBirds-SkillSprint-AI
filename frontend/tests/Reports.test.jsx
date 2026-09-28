import { render, act, fireEvent } from "@testing-library/react";
import { expect, test, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import HrReports from "../src/pages/hr/Reports";
import * as apiClient from "../src/services/apiClient";

vi.mock("../src/services/apiClient", () => ({
  backendEnabled: vi.fn(() => true),
  apiRequest: vi.fn(),
  apiBlob: vi.fn(),
}));
vi.mock("../src/hooks/useAuth", () => ({ useAuth: () => ({ user: { name: "HR" } }) }));
const lang = { t: (k, vars) => (vars ? `${k}:${JSON.stringify(vars)}` : k), tv: k => k, pick: (o, f) => o?.[f], locale: "vi" };
vi.mock("../src/contexts/LanguageContext", () => ({ useLanguage: () => lang }));

const DATA = {
  "/learners": [{ enrollment_id: "1", name: "Linh", email: "linh@x.vn", department_code: "Customer Support", job_title: "CS",
    path_title: "Onboarding CS", percent: 40, best_quiz_percent: null, certificate: false, status: "in_progress", completed_at: null }],
  "/reports/role-coverage": [
    { role_id: "cs-exec", role_name: "CS", department: "Customer Support", mandatory_requirements: 15, path_id: "LP-1",
      path_title: "Onboarding CS", covered_requirements: 12, coverage_score: 80, traceability_score: 97, final_status: "verified_warning" },
    { role_id: "data-analyst", role_name: "Data", department: "Data", mandatory_requirements: 18, path_id: null,
      path_title: null, covered_requirements: null, coverage_score: null, traceability_score: null, final_status: null },
  ],
  "/reports/quiz-analytics": [],
  "/reports/documents": [],
  "/reports/alerts": [],
  "/reports/comparison": [],
};

beforeEach(() => {
  vi.clearAllMocks();
  apiClient.apiRequest.mockImplementation(url => Promise.resolve(DATA[url]));
});

async function renderPage() {
  let container;
  await act(async () => { container = render(<MemoryRouter><HrReports /></MemoryRouter>).container; });
  return container;
}

test("learner figures come from the API and a missing quiz score is a dash", async () => {
  const text = (await renderPage()).textContent;
  expect(text).toContain("Linh");
  expect(text).toContain("40%");
  expect(text).toMatch(/—/);
  expect(apiClient.apiRequest).toHaveBeenCalledTimes(Object.keys(DATA).length);
});

test("role coverage shows real scores, and dashes for a role without a published path", async () => {
  const container = await renderPage();
  await act(async () => { fireEvent.click([...container.querySelectorAll(".filter-tabs button")].find(b => b.textContent.startsWith("rep_tab_coverage"))); });
  const text = container.textContent;
  expect(text).toContain("12/15");
  expect(text).toContain("80%");
  expect(text).toContain("97%");
  expect(text).toContain("rep_no_published_path");
  // The average ignores the role with no data instead of counting it as 0%.
  expect(text).toContain("rep_kpi_avg_coverage80%");
});

test("no hard-coded figures remain", async () => {
  apiClient.apiRequest.mockImplementation(() => Promise.resolve([]));
  const text = (await renderPage()).textContent;
  for (const fake of ["98.5%", "86.8%", "86.4%", "DOC-SEC-99"]) expect(text).not.toContain(fake);
});
