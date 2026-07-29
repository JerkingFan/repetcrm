import { test, expect } from "@playwright/test";
import { registerAndOnboard } from "./helpers";

test.describe("Lesson create", () => {
  test("create lesson for student", async ({ page }) => {
    await registerAndOnboard(page);
    const studentName = `LessonKid ${Date.now()}`;

    await page.goto("/students");
    await page.getByRole("button", { name: "Добавить" }).click();
    await page.getByPlaceholder("Анна Иванова").fill(studentName);
    await page.locator("select").nth(0).selectOption({ label: "7 класс" });
    await page.locator("select").nth(1).selectOption({ label: "Математика" });
    await page.getByRole("button", { name: "Сохранить" }).click();
    await expect(page.getByText(studentName)).toBeVisible();

    await page.goto("/lessons/new");
    await page.getByLabel("Ученик").selectOption({ label: studentName });
    await page.getByRole("button", { name: /Создать/i }).click();

    await expect(page).toHaveURL(/\/lessons\/\d+/, { timeout: 20_000 });
    await expect(page.getByText(studentName)).toBeVisible();
  });
});
