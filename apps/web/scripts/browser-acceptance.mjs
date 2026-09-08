import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const baseUrl = (process.env.COMPATFORGE_BROWSER_BASE_URL ?? "http://127.0.0.1:3100").replace(
  /\/$/,
  "",
);
const artifactDir = path.resolve(
  process.cwd(),
  process.env.COMPATFORGE_BROWSER_ARTIFACT_DIR ?? "build/browser-acceptance",
);
const browserCandidates = process.env.CHROME_BIN
  ? [process.env.CHROME_BIN]
  : ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"];

mkdirSync(artifactDir, { recursive: true });

function runBrowser(args) {
  for (const command of browserCandidates) {
    const result = spawnSync(command, args, {
      encoding: "utf8",
      maxBuffer: 24 * 1024 * 1024,
    });
    if (result.error?.code === "ENOENT") continue;
    if (result.error) throw result.error;
    if (result.status !== 0) {
      throw new Error(
        `${command} exited with ${result.status}: ${(result.stderr ?? "").trim()}`,
      );
    }
    return { command, stdout: result.stdout ?? "", stderr: result.stderr ?? "" };
  }
  throw new Error(`No supported Chrome/Chromium binary found: ${browserCandidates.join(", ")}`);
}

async function waitForServer() {
  let lastError = "no response";
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(`${baseUrl}/`, { redirect: "manual" });
      if (response.status >= 200 && response.status < 500) return;
      lastError = `HTTP ${response.status}`;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Browser acceptance target did not become reachable: ${lastError}`);
}

function dumpDom(url) {
  const result = runBrowser([
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--hide-scrollbars",
    "--virtual-time-budget=2500",
    "--dump-dom",
    url,
  ]);
  return { browser: result.command, html: result.stdout };
}

function screenshot(name, url, width, height) {
  const outputPath = path.join(artifactDir, `${name}.png`);
  runBrowser([
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--hide-scrollbars",
    `--window-size=${width},${height}`,
    `--screenshot=${outputPath}`,
    url,
  ]);
  return outputPath;
}

const cases = [
  {
    name: "home",
    pathname: "/",
    status: 200,
    includes: [
      "Will this hardware actually work?",
      "Evidence-first compatibility",
      "Browse devices",
    ],
  },
  {
    name: "device-search",
    pathname: "/devices?q=FT232R",
    status: 200,
    includes: ["1 result(s)", "FTDI", "FT232R", "usb:0403:6001"],
  },
  {
    name: "device-detail",
    pathname: "/devices/ftdi-ft232r",
    status: 200,
    includes: [
      "Documented platform scope.",
      "Configuration-level reports.",
      "Aspire 14 AI (2025)",
    ],
  },
  {
    name: "checker-result",
    pathname:
      "/check?device=usb%3A0403%3A6001&os=windows&version=11&architecture=arm64&connection=direct_port",
    status: 200,
    includes: [
      "Observed compatibility",
      "Vendor support",
      "supported with conditions",
      "Related observation exists, but it does not match this query.",
    ],
  },
  {
    name: "coverage",
    pathname: "/coverage",
    status: 200,
    includes: [
      "See what the corpus can—and cannot—answer.",
      "Coverage is not confidence.",
      "Latest evidence",
    ],
  },
  {
    name: "submissions-unauthenticated",
    pathname: "/submissions",
    status: 200,
    includes: ["Reproductions enter a review queue, not the evidence corpus."],
    includesAny: [
      [
        "Community auth is not configured",
        "Use GitHub only to establish a Supabase user identity.",
      ],
    ],
  },
  {
    name: "custom-not-found",
    pathname: "/devices/not-a-reviewed-device",
    status: 404,
    includes: ["That evidence page does not exist.", "Browse devices"],
  },
];

await waitForServer();
const versionProbe = runBrowser(["--version"]);
const results = [];
let failure = null;

try {
  for (const testCase of cases) {
    const url = `${baseUrl}${testCase.pathname}`;
    const response = await fetch(url, { redirect: "manual" });
    if (response.status !== testCase.status) {
      throw new Error(
        `${testCase.name}: expected HTTP ${testCase.status}, received ${response.status}`,
      );
    }

    const { html } = dumpDom(url);
    const assertedHtml = html.replaceAll("<!-- -->", "");
    if (!assertedHtml.includes("<main")) {
      throw new Error(`${testCase.name}: browser DOM did not contain the application <main>`);
    }
    for (const expected of testCase.includes) {
      if (!assertedHtml.includes(expected)) {
        throw new Error(`${testCase.name}: browser DOM did not contain ${JSON.stringify(expected)}`);
      }
    }
    for (const alternatives of testCase.includesAny ?? []) {
      if (!alternatives.some((expected) => assertedHtml.includes(expected))) {
        throw new Error(
          `${testCase.name}: browser DOM did not contain any of ${JSON.stringify(alternatives)}`,
        );
      }
    }
    if (
      assertedHtml.includes("Application error") ||
      assertedHtml.includes("Internal Server Error")
    ) {
      throw new Error(`${testCase.name}: browser DOM contained a framework/runtime error marker`);
    }

    results.push({
      name: testCase.name,
      pathname: testCase.pathname,
      status: response.status,
      required_text: testCase.includes,
      alternative_text_groups: testCase.includesAny ?? [],
      dom_bytes: Buffer.byteLength(html),
    });
  }

  screenshot("home-desktop", `${baseUrl}/`, 1440, 1000);
  screenshot("home-mobile", `${baseUrl}/`, 390, 844);
  screenshot(
    "checker-desktop",
    `${baseUrl}/check?device=usb%3A0403%3A6001&os=windows&version=11&architecture=arm64&connection=direct_port`,
    1440,
    1200,
  );
} catch (error) {
  failure = error instanceof Error ? error.message : String(error);
}

const report = {
  report_version: 1,
  base_url: baseUrl,
  browser: versionProbe.stdout.trim(),
  passed: failure === null,
  cases: results,
  failure,
};
writeFileSync(
  path.join(artifactDir, "browser-acceptance.json"),
  `${JSON.stringify(report, null, 2)}\n`,
  "utf8",
);

const summary = [
  "# Browser acceptance",
  "",
  `- Target: \`${baseUrl}\``,
  `- Browser: \`${report.browser}\``,
  `- Result: **${report.passed ? "PASS" : "FAIL"}**`,
  `- Completed cases: **${results.length}/${cases.length}**`,
  "",
  "| Case | HTTP | Required markers | Alternative groups |",
  "| --- | ---: | ---: | ---: |",
  ...results.map(
    (item) =>
      `| \`${item.name}\` | ${item.status} | ${item.required_text.length} | ${item.alternative_text_groups.length} |`,
  ),
  "",
  failure ? `Failure: ${failure}` : "All required routes rendered their reviewed acceptance markers.",
  "",
].join("\n");
writeFileSync(path.join(artifactDir, "summary.md"), summary, "utf8");

console.log(summary);
if (failure) process.exitCode = 1;
