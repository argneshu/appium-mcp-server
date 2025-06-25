#!/usr/bin/env node

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const venvDir = path.join(__dirname, "..", ".venv");

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
      const result = require("child_process").execSync(`${candidate} --version 2>&1`, {
        encoding: 'utf8',
        stdio: 'pipe'
      });
      
      const versionMatch = result.match(/Python (\d+)\.(\d+)/);
      if (versionMatch) {
        const major = parseInt(versionMatch[1]);
        const minor = parseInt(versionMatch[2]);
        
        if (major > 3 || (major === 3 && minor >= 10)) {
          console.error(`Using Python: ${candidate} (${result.trim()})`);
          return candidate;
        }
      }
    } catch (e) {
      // Command not found or failed, try next candidate
      continue;
    }
  }
  
  throw new Error("No compatible Python version found. Please install Python 3.10 or higher.");
};

const ensureVirtualEnv = () => {
  return new Promise((resolve, reject) => {
    if (!fs.existsSync(venvDir)) {
      console.error("Creating Python virtual environment");
      
      let python;
      try {
        python = findCompatiblePython();
      } catch (e) {
        return reject(e.message);
      }
      
      const venv = spawn(python, ["-m", "venv", venvDir]);

      venv.on("close", (code) => {
        if (code !== 0) return reject("Failed to create virtualenv");

        console.error("Installing Python dependencies");
        const pipPath = path.join(
          venvDir,
          process.platform === "win32" ? "Scripts" : "bin",
          "pip"
        );
        const pipInstall = spawn(
          pipPath,
          ["install", "--quiet", "--disable-pip-version-check", "--no-input", "-r", "requirements.txt"],
          {
            cwd: path.join(__dirname, ".."),
            stdio: ["ignore", process.stderr, process.stderr], // critical
          }
        );
        pipInstall.on("close", (code2) => {
          if (code2 !== 0) return reject("Failed to install dependencies");
          resolve();
        });
      });
    } else {
      resolve();
    }
  });
};

const startPythonServer = () => {
  // Use APP_MCP_PYTHON env var if defined, otherwise fallback to .venv/bin/python
  const pythonPath = process.env.APP_MCP_PYTHON || path.join(
    venvDir,
    process.platform === "win32" ? "Scripts" : "bin",
    "python"
  );
  const serverScript = path.join(__dirname, "..", "src", "mcp_server.py");

  const server = spawn(pythonPath, [serverScript], {
    stdio: "inherit",
  });

  server.on("close", (code) => {
    console.error(`MCP server exited with code ${code}`);
  });
};

(async () => {
  try {
    await ensureVirtualEnv();
    startPythonServer();
  } catch (e) {
    console.error("MCP server failed to start:", e);
  }
})();