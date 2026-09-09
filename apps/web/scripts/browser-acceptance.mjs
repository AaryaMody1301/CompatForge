import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const baseUrl = (process.env.COMPATFORGE_BROWSER_BASE_URL ?? "http://127.0.0.1:3100").replace(
  /\/$/,
  "",
);
const expectedCommit = process.env.COMPATFORGE_EXPECTED_COMMIT?.trim() || null;
const artifactDir = path.resolve(
  process.cwd(),
  process.env.COMPATFORGE_BROWSER_ARTIFACT_DIR ?? "build/browser-acceptance",
);
const browserCandidates = process.env.CHROME_BIN
  ? [process.env.CHROME_BIN]
  : ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"];
const fullCommitPattern = /^[0-9a-f]{40}$/;
const localTarget = ["localhost", "127.0.0.1"].includes(new URL(baseUrl).hostname);
const requiredSecurityHeaders = {
  "content-security-policy": ["base-uri 'self'", "frame-ancestors 'none'", "object-src 'none'"],
  "permissions-policy": ["camera=()", "microphone=()", "geolocation=()", "browsing-topics=()"],
  "referrer-policy": ["strict-origin-when-cross-origin"],
  "strict-transport-security": ["max-age=63072000", "includeSubDomains", "preload"],
  "x-content-type-options": ["nosniff"],
  "x-frame-options": ["DENY"],
};

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

function assertSecurityHeaders(name, response) {
  const observed = {};
  for (const [headerName, expectedParts] of Object.entries(requiredSecurityHeaders)) {
    const value = response.headers.get(headerName);
    if (!value) {
      throw new Error(`${name}: response did not include required ${headerName} header`);
    }
    for (const expected of expectedParts) {
      if (!value.includes(expected)) {
        throw new Error(
          `${name}: ${headerName} did not contain ${JSON.stringify(expected)}; received ${JSON.stringify(value)}`,
        );
      }
    }
    observed[headerName] = value;
  }
  if (response.headers.has("x-powered-by")) {
    throw new Error(`${name}: response exposed the X-Powered-By framework header`);
  }
  return observed;
}

function assertDeploymentCommit(name, response) {
  const observed = response.headers.get("x-compatforge-commit");
  if (!observed) {
    throw new Error(`${name}: response did not include X-CompatForge-Commit`);
  }
  if (expectedCommit) {
    if (!fullCommitPattern.test(expectedCommit)) {
      throw new Error(`Configured COMPATFORGE_EXPECTED_COMMIT is not a full Git SHA`);
    }
    if (observed !== expectedCommit) {
      throw new Error(
        `${name}: deployment commit ${JSON.stringify(observed)} did not match ${expectedCommit}`,
      );
    }
    return observed;
  }
  if (fullCommitPattern.test(observed) || (localTarget && observed === "local")) {
    return observed;
  }
  throw new Error(`${name}: deployment commit header was not a full Git SHA`);
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
    name: "checker-invalid-device",
    pathname:
      "/check?device=usb%3ADEAD%3ABEEF&os=windows&version=11&architecture=arm64&connection=unspecified&host_manufacturer=Acer&host_model=Aspire%2014%20AI%20%282025%29",
    status: 200,
    includes: [
      "Invalid configuration.",
      "device is outside the reviewed checker options.",
      "No compatibility claim was generated.",
    ],
    excludes: ["<p class=\"eyebrow\">Result</p>", "works with conditions"],
  },
  {
    name: "checker-invalid-architecture",
    pathname:
      "/check?device=usb%3A0403%3A6001&os=windows&version=11&architecture=sparc&connection=unspecified&host_manufacturer=Acer&host_model=Aspire%2014%20AI%20%282025%29",
    status: 200,
    includes: [
      "Invalid configuration.",
      "architecture is outside the reviewed checker options.",
      "No compatibility claim was generated.",
    ],
    excludes: ["<p class=\"eyebrow\">Result</p>", "works with conditions"],
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
    const securityHeaders = assertSecurityHeaders(testCase.name, response);
    const deploymentCommit = assertDeploymentCommit(testCase.name, response);

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
    for (const forbidden of testCase.excludes ?? []) {
      if (assertedHtml.includes(forbidden)) {
        throw new Error(`${testCase.name}: browser DOM contained forbidden ${JSON.stringify(forbidden)}`);
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
      forbidden_text: testCase.excludes ?? [],
      alternative_text_groups: testCase.includesAny ?? [],
      security_headers: securityHeaders,
      deployment_commit: deploymentCommit,
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
  report_version: 4,
  base_url: baseUrl,
  browser: versionProbe.stdout.trim(),
  expected_commit: expectedCommit,
  required_security_headers: requiredSecurityHeaders,
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
  `- Required security headers: **${Object.keys(requiredSecurityHeaders).length}**`,
  `- Expected commit: \`${expectedCommit ?? (localTarget ? "local or full SHA" : "full SHA")}\``,
  "",
  "| Case | HTTP | Required markers | Forbidden markers | Alternative groups | Security headers | Commit |",
  "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
  ...results.map(
    (item) =>
      `| \`${item.name}\` | ${item.status} | ${item.required_text.length} | ${item.forbidden_text.length} | ${item.alternative_text_groups.length} | ${Object.keys(item.security_headers).length} | \`${item.deployment_commit}\` |`,
  ),
  "",
  failure
    ? `Failure: ${failure}`
    : "All required routes rendered their reviewed acceptance markers, rejected forbidden markers, security headers, and deployment commit provenance.",
  "",
].join("\n");
writeFileSync(path.join(artifactDir, "summary.md"), summary, "utf8");

console.log(summary);
if (failure) process.exitCode = 1;
