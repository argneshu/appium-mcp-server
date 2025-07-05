import sys, asyncio, pathlib
from mcp.types import TextContent

PROJECT_ROOT = pathlib.Path.home() / "generated-framework"

async def handle_write_files_batch(arguments: dict) -> TextContent:
    files = arguments.get("files", [])
    batch_size = arguments.get("batch_size", 10)
    retry_limit = arguments.get("retry_limit", 2)

    if not files:
        return TextContent(type="text",
                           text="⚠️ No files provided to write.")

    total, ok, failed = len(files), 0, []

    # Split into chunks
    for i in range(0, total, batch_size):
        batch = files[i:i+batch_size]
        print(f"🌀 Batch {i//batch_size+1} / {len(batch)} files",
              file=sys.stderr)          # 👉 stderr, not stdout

        for file in batch:
            path, content = file.get("path"), file.get("content")
            if not path or content is None:
                failed.append((path or "<missing>", "Missing path/content"))
                continue

            full = PROJECT_ROOT / path
            full.parent.mkdir(parents=True, exist_ok=True)

            for attempt in range(1, retry_limit + 2):
                try:
                    full.write_text(content, encoding="utf-8")
                    ok += 1
                    break
                except Exception as e:
                    if attempt == retry_limit + 1:
                        failed.append((path, str(e)))
                    await asyncio.sleep(0.1)

            await asyncio.sleep(0.05)

    summary = [f"✅ Wrote {ok}/{total} file(s) to ~/generated-framework"]
    if failed:
        summary.append(f"❌ {len(failed)} file(s) failed:")
        summary += [f"- {p}: {err}" for p, err in failed]

    return TextContent(type="text", text="\n".join(summary))
