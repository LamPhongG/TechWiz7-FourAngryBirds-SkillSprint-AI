import { render, act, fireEvent, screen, cleanup } from "@testing-library/react";
import { expect, test, vi, beforeEach, afterEach } from "vitest";
import CreateEmployeeModal from "../src/components/CreateEmployeeModal";
import ChangePasswordModal from "../src/components/ChangePasswordModal";
import * as apiClient from "../src/services/apiClient";

vi.mock("../src/services/apiClient", () => ({
  backendEnabled: vi.fn(() => true),
  apiRequest: vi.fn(),
}));
const changePassword = vi.fn();
vi.mock("../src/hooks/useAuth", () => ({ useAuth: () => ({ changePassword }) }));
const lang = { t: (k, vars) => (vars ? `${k}:${JSON.stringify(vars)}` : k), tv: k => k, pick: (o, f) => o?.[f], locale: "en" };
vi.mock("../src/contexts/LanguageContext", () => ({ useLanguage: () => lang }));

const DRAFT = {
  name: "John Doe", email: "john.doe@gmail.com", years_of_experience: 3, experience_level: "Intermediate",
  previous_experience: "ABC Corp", competencies: ["Communication", "CRM"], warnings: ["cv_warn_no_skills"],
};
const USER = { id: "USR-1", email: "john.doe@gmail.com", name: "John Doe", user_role: "employee", password_is_temporary: true };

// Vitest globals not enabled so Testing Library does not auto-cleanup DOM; reset mocks between tests
beforeEach(() => { vi.clearAllMocks(); apiClient.apiRequest.mockReset(); changePassword.mockReset(); });
afterEach(cleanup);

async function uploadCv() {
  const onCreated = vi.fn();
  const { container } = render(<CreateEmployeeModal open onClose={() => {}} onCreated={onCreated} />);
  const file = new File(["cv"], "an.docx");
  await act(async () => { fireEvent.change(container.querySelector("#cv-file"), { target: { files: [file] } }); });
  return { container, onCreated };
}

test("the CV draft prefills an editable form and the warnings are shown", async () => {
  apiClient.apiRequest.mockResolvedValueOnce(DRAFT);
  const { container } = await uploadCv();
  const [url, init] = apiClient.apiRequest.mock.calls[0];
  expect(url).toBe("/users/cv/parse");
  expect(init.body).toBeInstanceOf(FormData);
  expect(container.querySelector("#cv-name").value).toBe("John Doe");
  expect(container.querySelector("#cv-email").value).toBe("john.doe@gmail.com");
  expect(container.querySelector("#cv-level").value).toBe("Intermediate");
  expect(container.querySelector("#cv-skills").value).toBe("Communication, CRM");
  expect(container.textContent).toContain("cv_warn_no_skills");
});

test("a position is required before the account is created", async () => {
  apiClient.apiRequest.mockResolvedValueOnce(DRAFT);
  const { container } = await uploadCv();
  await act(async () => { fireEvent.submit(container.querySelector("form")); });
  expect(apiClient.apiRequest).toHaveBeenCalledTimes(1);
  expect(container.textContent).toContain("cv_err_required");
});

test("creating the account sends the edited fields and shows the password only when the email failed", async () => {
  apiClient.apiRequest.mockResolvedValueOnce(DRAFT).mockResolvedValueOnce({
    user: USER, email_sent: false, temporary_password: "Hk2$Y?34%VSb",
  });
  const { container, onCreated } = await uploadCv();
  fireEvent.change(container.querySelector("#cv-position"), { target: { value: "cs-exec" } });
  fireEvent.change(container.querySelector("#cv-skills"), { target: { value: "Communication, , CRM " } });
  await act(async () => { fireEvent.submit(container.querySelector("form")); });

  const [url, init] = apiClient.apiRequest.mock.calls[1];
  expect(url).toBe("/users/from-cv");
  expect(init.body).toEqual({
    name: "John Doe", email: "john.doe@gmail.com", job_position_id: "cs-exec",
    experience_level: "Intermediate", previous_experience: "ABC Corp", competencies: ["Communication", "CRM"],
  });
  expect(onCreated).toHaveBeenCalled();
  expect(screen.getByTestId("cv-email-failed")).toBeTruthy();
  expect(container.querySelector("#cv-temp-password").textContent).toBe("Hk2$Y?34%VSb");
});

test("when the email is sent the password is not on screen", async () => {
  apiClient.apiRequest.mockResolvedValueOnce(DRAFT).mockResolvedValueOnce({ user: USER, email_sent: true, temporary_password: null });
  const { container } = await uploadCv();
  fireEvent.change(container.querySelector("#cv-position"), { target: { value: "cs-exec" } });
  await act(async () => { fireEvent.submit(container.querySelector("form")); });
  expect(screen.getByTestId("cv-email-sent")).toBeTruthy();
  expect(container.querySelector("#cv-temp-password")).toBeNull();
});

test("skipping the CV upload goes straight to an empty form, no parse call made", async () => {
  const { container } = render(<CreateEmployeeModal open onClose={() => {}} onCreated={() => {}} />);
  await act(async () => { fireEvent.click(screen.getByText("cv_skip_manual")); });
  expect(apiClient.apiRequest).not.toHaveBeenCalled();
  expect(container.querySelector("#cv-name").value).toBe("");
  expect(container.querySelector("#cv-email").value).toBe("");
  await act(async () => { fireEvent.submit(container.querySelector("form")); });
  expect(container.textContent).toContain("cv_err_required");
});

test("an unreadable CV shows the backend reason and stays on the upload step", async () => {
  const err = Object.assign(new Error("CV could not be read"), { code: "err_cv_unreadable", vars: { reason: "NO_TEXT_LAYER" } });
  apiClient.apiRequest.mockRejectedValueOnce(err);
  const { container } = await uploadCv();
  expect(container.textContent).toContain("err_cv_unreadable");
  expect(container.querySelector("#cv-file")).toBeTruthy();
});

function fillPassword(container, current, next, confirm) {
  fireEvent.change(container.querySelector("#pwd-current"), { target: { value: current } });
  fireEvent.change(container.querySelector("#pwd-next"), { target: { value: next } });
  fireEvent.change(container.querySelector("#pwd-confirm"), { target: { value: confirm } });
}

test("change password checks length and confirmation before calling the API", async () => {
  const { container } = render(<ChangePasswordModal open onClose={() => {}} />);
  fillPassword(container, "Old#12345", "short", "short");
  await act(async () => { fireEvent.submit(container.querySelector("form")); });
  expect(container.textContent).toContain("pwd_err_short");
  fillPassword(container, "Old#12345", "NewPass#2026", "NewPass#2027");
  await act(async () => { fireEvent.submit(container.querySelector("form")); });
  expect(container.textContent).toContain("pwd_err_mismatch");
  expect(changePassword).not.toHaveBeenCalled();
});

test("change password reports a wrong current password and closes on success", async () => {
  const onClose = vi.fn();
  const onDone = vi.fn();
  const { container } = render(<ChangePasswordModal open onClose={onClose} onDone={onDone} />);
  changePassword.mockRejectedValueOnce(Object.assign(new Error("bad"), { code: "err_current_password", status: 400 }));
  fillPassword(container, "wrong", "NewPass#2026", "NewPass#2026");
  await act(async () => { fireEvent.submit(container.querySelector("form")); });
  expect(container.textContent).toContain("err_current_password");
  expect(onClose).not.toHaveBeenCalled();

  changePassword.mockResolvedValueOnce({});
  fillPassword(container, "Old#12345", "NewPass#2026", "NewPass#2026");
  await act(async () => { fireEvent.submit(container.querySelector("form")); });
  expect(changePassword).toHaveBeenLastCalledWith("Old#12345", "NewPass#2026");
  expect(onClose).toHaveBeenCalled();
  expect(onDone).toHaveBeenCalledWith("pwd_changed");
});
