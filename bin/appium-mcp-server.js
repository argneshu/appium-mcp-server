#!/usr/bin/env node

const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const venvDir = path.join(__dirname, "..", ".venv");
const sitePackagesPath = path.join(
  venvDir,
  "lib",
  "python3.12",
  "site-packages"
);

// Try to find a compatible Python version (3.10+)
const findCompatiblePython = () => {
  const candidates = [
    "python3.12",
    "python3.11",
    "python3.10",
    "python3",
    "python"
  ];

  for (const candidate of candidates) {
    try {
      const result = execSync(`${candidate} --version`, {
        encoding: "utf8",
        stdio: "pipe"
      });

      const match = result.match(/Python (\d+)\.(\d+)/);
      if (match) {
        const major = parseInt(match[1]);
        const minor = parseInt(match[2]);
        if (major > 3 || (major === 3 && minor >= 10)) {
          console.error(`Using Python: ${candidate} (${result.trim()})`);
          return candidate;
        }
      }
    } catch (err) {
      continue; // Try next candidate
    }
  }

  throw new Error("❌ No compatible Python version (>=3.10) found.");
};

// Skip creating virtualenv on runtime, since .venv is bundled
const ensureVirtualEnv = () => {
  return new Promise((resolve, reject) => {
    if (!fs.existsSync(sitePackagesPath)) {
      return reject("❌ site-packages not found in bundled .venv. Did you forget to shrink and include it?");
    }
    resolve();
  });
};

const startPythonServer = () => {
  const serverScript = path.join(__dirname, "..", "src", "mcp_server.py");
  const systemPython = process.env.APP_MCP_PYTHON || findCompatiblePython();

  console.error(`🚀 Starting MCP server using ${systemPython}`);
  console.error(`🔧 Injecting PYTHONPATH = ${sitePackagesPath}`);

  const server = spawn(systemPython, [serverScript], {
    stdio: "inherit",
    env: {
      ...process.env,
      PYTHONPATH: sitePackagesPath
    }
  });

  server.on("close", (code) => {
    console.error(`❌ MCP server exited with code ${code}`);
  });
};

(async () => {
  try {
    await ensureVirtualEnv();
    startPythonServer();
  } catch (err) {
    console.error("🚨 MCP server failed to start:", err);
  }
})();
