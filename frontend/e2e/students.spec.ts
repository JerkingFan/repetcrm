import { test, expect } from "@playwright/test";
import { registerAndOnboard } from "./helpers";

test.describe("Student CRUD", () => {
  test.beforeEach(async ({ page }) => {
    await registerAndOnboard(page);
  });

  test("create student and find in list", async ({ page }) => {
    const studentName = `E2E Student ${Date.now()}`;

    await page.goto("/students");
    await page.getByRole("button", { name: "Добавить" }).click();
    await page.getByPlaceholder("Анна Иванова").fill(studentName);
    await page.locator("select").nth(0).selectOption({ label: "7 класс" });
    await page.locator("select").nth(1).selectOption({ label: "Математика" });
    await page.getByRole("button", { name: "Сохранить" }).click();

    await expect(page.getByText(studentName)).toBeVisible({ timeout: 15_000 });
  });
});
