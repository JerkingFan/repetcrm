import { test, expect } from "@playwright/test";
import { login, registerAndOnboard, uniqueEmail } from "./helpers";

test.describe("Auth flow", () => {
  test("register, onboarding, logout and login", async ({ page }) => {
    const email = await registerAndOnboard(page);

    await page.goto("/dashboard");
    await page.getByRole("button", { name: "Выйти" }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });

    await login(page, email);
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("login rejects wrong password", async ({ page }) => {
    const email = uniqueEmail("auth-bad");
    await registerAndOnboard(page, email);

    await page.goto("/dashboard");
    await page.getByRole("button", { name: "Выйти" }).click();

    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Пароль").fill("WrongPassword1!");
    await page.getByRole("button", { name: "Войти" }).click();
    await expect(page.getByText(/неверн|ошибк/i)).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });
});
