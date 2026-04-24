import { expect, test, type Page, type APIRequestContext } from "@playwright/test";

async function readAccessToken(page: Page) {
  const accessToken = await page.evaluate(() => {
    for (const key of Object.keys(window.localStorage)) {
      if (!key.startsWith("oidc.user:")) {
        continue;
      }

      const rawValue = window.localStorage.getItem(key);
      if (!rawValue) {
        continue;
      }

      const parsed = JSON.parse(rawValue) as { access_token?: unknown };
      if (typeof parsed.access_token === "string" && parsed.access_token.length > 0) {
        return parsed.access_token;
      }
    }

    return null;
  });

  expect(accessToken).toBeTruthy();
  return accessToken as string;
}

async function seedModel(request: APIRequestContext, accessToken: string) {
  const suffix = Date.now().toString();
  const modelName = `Prompt 7 Model ${suffix}`;
  const modelVersion = `1.0.${suffix}`;
  const modelLabel = `${modelName} ${modelVersion}`;

  const response = await request.post("http://127.0.0.1:8000/api/v1/models", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      name: modelName,
      version: modelVersion,
      task: "detect",
      path: `/models/${suffix}.onnx`,
      format: "onnx",
      classes: ["person", "car", "truck"],
      input_shape: { h: 640, w: 640, c: 3 },
      sha256: "a".repeat(64),
      size_bytes: 123456,
      license: "Apache-2.0",
    },
  });

  expect(response.ok()).toBeTruthy();

  return { modelLabel, suffix };
}

test("real login creates a site and camera through the prompt 7 flows", async ({
  page,
  request,
}) => {
  const suffix = Date.now().toString();
  const siteName = `Prompt 7 Site ${suffix}`;
  const cameraName = `Prompt 7 Camera ${suffix}`;

  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await expect(page).toHaveURL(/\/live$/);
  const accessToken = await readAccessToken(page);
  const { modelLabel } = await seedModel(request, accessToken);
  await page.getByRole("link", { name: "Sites" }).click();
  await page.getByRole("button", { name: "Add site" }).click();
  await page.getByLabel("Site name").fill(siteName);
  await page.getByLabel("Time zone").fill("Europe/Zurich");
  await page.getByRole("button", { name: "Save site" }).click();
  await expect(page.getByRole("cell", { name: siteName })).toBeVisible();

  await page.getByRole("link", { name: "Cameras" }).click();
  await page.getByRole("button", { name: "Add camera" }).click();
  await page.getByLabel("Camera name").fill(cameraName);
  await page.getByLabel("Site").selectOption({ label: siteName });
  await page.getByLabel("RTSP URL").fill("rtsp://camera.local/live");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("Primary model").selectOption({ label: modelLabel });
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("Browser delivery profile").selectOption("720p10");
  await page.getByRole("button", { name: "Next" }).click();

  for (let count = 0; count < 4; count += 1) {
    await page.getByRole("button", { name: "Add source point" }).click();
    await page.getByRole("button", { name: "Add destination point" }).click();
  }

  await page.getByLabel("Reference distance (m)").fill("12.5");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Create camera" }).click();

  await expect(page.getByRole("cell", { name: cameraName })).toBeVisible();
});
