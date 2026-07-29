import { expect, type Page } from "@playwright/test";

export function uniqueEmail(prefix = "e2e") {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@test.example`;
}

export const E2E_PASSWORD = "SecurePass99!";

export async function registerAndOnboard(page: Page, email = uniqueEmail()) {
  await page.goto("/register");
  await page.getByLabel("Имя").fill("E2E Tutor");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/Пароль/).fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Создать аккаунт" }).click();
  await expect(page).toHaveURL(/\/onboarding/, { timeout: 20_000 });

  await page.getByRole("button", { name: "Далее" }).click();
  await page.getByRole("button", { name: "Математика" }).click();
  await page.getByRole("button", { name: "Далее" }).click();
  await page.getByRole("button", { name: "7 класс" }).click();
  await page.getByRole("button", { name: "Далее" }).click();
  await page.getByRole("button", { name: "Далее" }).click();
  await page.getByRole("button", { name: "Начать работу" }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });

  return email;
}

export async function login(page: Page, email: string, password = E2E_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).toHaveURL(/\/(dashboard|onboarding)/, { timeout: 20_000 });
}
