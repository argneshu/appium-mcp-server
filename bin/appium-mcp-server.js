#!/usr/bin/env node

const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const venvDir = path.join(__dirname, "..", ".venv");

// Try to find a compatible Python version (3.10+)
const findCompatiblePython = () => {
  const candidates = ["python3.12", "python3.11", "python3.10", "python3", "python"];

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
          return { cmd: candidate, minor };
        }
      }
    } catch (err) {
      continue;
    }
  }

  throw new Error("❌ No compatible Python version (>=3.10) found.");
};

// Dynamically resolve site-packages path based on detected Python version
const getSitePackagesPath = (minorVersion) => {
  return path.join(venvDir, "lib", `python3.${minorVersion}`, "site-packages");
};

// Build .venv if not present (instead of assuming bundled)
const ensureVirtualEnv = (pythonCmd, sitePackagesPath) => {
  return new Promise((resolve, reject) => {
    if (fs.existsSync(sitePackagesPath)) {
      console.error(`✅ Found existing .venv at ${sitePackagesPath}`);
      return resolve();
    }

    console.error("⏳ First run setup — this may take 1-2 minutes...");
    console.error("⚠️  .venv not found. Building from requirements.txt...");

    const requirementsPath = path.join(__dirname, "..", "requirements.txt");
    if (!fs.existsSync(requirementsPath)) {
      return reject("❌ requirements.txt not found. Cannot build .venv.");
    }

    try {
      execSync(`${pythonCmd} -m venv ${venvDir}`, { stdio: "inherit" });
      execSync(`${venvDir}/bin/pip install --upgrade pip setuptools wheel`, { stdio: "inherit" });
      execSync(`${venvDir}/bin/pip install -r ${requirementsPath}`, { stdio: "inherit" });
      console.error("✅ .venv built successfully!");
      resolve();
    } catch (err) {
      reject(`❌ Failed to build .venv: ${err.message}`);
    }
  });
};

const startPythonServer = (pythonCmd, sitePackagesPath) => {
  const serverScript = path.join(__dirname, "..", "src", "mcp_server.py");
  const systemPython = process.env.APP_MCP_PYTHON || pythonCmd;

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
    const { cmd, minor } = findCompatiblePython();
    const sitePackagesPath = getSitePackagesPath(minor);
    await ensureVirtualEnv(cmd, sitePackagesPath);
    startPythonServer(cmd, sitePackagesPath);
  } catch (err) {
    console.error("🚨 MCP server failed to start:", err);
  }
})();