import { expect, test, type Page, type APIRequestContext } from "@playwright/test";

function workspaceLink(page: Page, group: "Intelligence" | "Control", name: string) {
  return page
    .getByRole("navigation", { name: group })
    .getByRole("link", { name });
}

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

  const response = await request.post("http://127.0.0.1:8000/api/v1/models", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    data: {
      name: modelName,
      version: modelVersion,
      task: "detect",
      path: `/models/${suffix}.engine`,
      format: "engine",
      classes: ["person", "car", "truck"],
      input_shape: { h: 640, w: 640, c: 3 },
      sha256: "a".repeat(64),
      size_bytes: 123456,
      license: "Apache-2.0",
    },
  });

  expect(response.ok()).toBeTruthy();
  const model = (await response.json()) as { id: string };
  expect(model.id).toBeTruthy();

  return { modelId: model.id };
}

test("real login creates a site and camera through the prompt 7 flows", async ({
  page,
  request,
}) => {
  const suffix = Date.now().toString();
  const siteName = `Prompt 7 Site ${suffix}`;
  const cameraName = `Prompt 7 Camera ${suffix}`;
  const rtspUrl = `rtsp://127.0.0.1:1/prompt7-${suffix}`;

  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await expect(page).toHaveURL(/\/live$/);
  const accessToken = await readAccessToken(page);
  const { modelId } = await seedModel(request, accessToken);
  await workspaceLink(page, "Control", "Sites").click();
  await page.getByRole("button", { name: "Add site" }).click();
  await page.getByLabel("Site name").fill(siteName);
  await page.getByLabel("Time zone").fill("Europe/Zurich");
  await page.getByRole("button", { name: "Save site" }).click();
  await expect(page.getByRole("cell", { name: siteName })).toBeVisible();

  await workspaceLink(page, "Control", "Scenes").click();
  const sceneWorkspace = page.getByTestId("scene-setup-workspace");
  await sceneWorkspace.getByRole("button", { name: "Add scene" }).click();
  await sceneWorkspace.getByLabel("Camera name").fill(cameraName);
  await sceneWorkspace.getByLabel("Site", { exact: true }).selectOption({ label: siteName });
  await sceneWorkspace.getByLabel("RTSP URL").fill(rtspUrl);
  await sceneWorkspace.getByRole("button", { name: "Next" }).click();
  await sceneWorkspace.getByLabel("Primary model").selectOption(modelId);
  await sceneWorkspace.getByRole("button", { name: "Next" }).click();
  await sceneWorkspace.getByLabel("Browser delivery profile").selectOption("720p10");
  await sceneWorkspace.getByRole("button", { name: "Next" }).click();

  for (let count = 0; count < 4; count += 1) {
    await sceneWorkspace.getByRole("button", { name: "Add source point" }).click();
    await sceneWorkspace.getByRole("button", { name: "Add destination point" }).click();
  }

  await sceneWorkspace.getByLabel("Reference distance (m)").fill("12.5");
  await sceneWorkspace.getByRole("button", { name: "Next" }).click();
  const createCameraResponsePromise = page.waitForResponse(
    (response) =>
      response.url() === "http://127.0.0.1:8000/api/v1/cameras" &&
      response.request().method() === "POST",
    { timeout: 60_000 },
  );

  await sceneWorkspace.getByRole("button", { name: "Create camera" }).click();
  const createCameraResponse = await createCameraResponsePromise;

  if (!createCameraResponse.ok()) {
    throw new Error(
      `Camera create failed with ${createCameraResponse.status()}: ${await createCameraResponse.text()}`,
    );
  }

  await page.reload();
  await expect(page).toHaveURL(/\/cameras$/);
  await expect(page.getByRole("cell", { name: cameraName })).toBeVisible();
});
