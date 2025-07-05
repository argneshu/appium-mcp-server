import asyncio
import pathlib
from mcp.types import TextContent

PROJECT_ROOT = pathlib.Path.home() / "generated-framework"

async def handle_write_files_batch(arguments: dict) -> TextContent:
    files = arguments.get("files", [])
    batch_size = arguments.get("batch_size", 10)  # Optional override
    retry_limit = arguments.get("retry_limit", 2)  # Max retries per file

    if not files:
        return TextContent(type="text", text="⚠️ No files provided to write.")

    total_files = len(files)
    success_count = 0
    failed_files = []

    # Split files into chunks of batch_size
    for i in range(0, total_files, batch_size):
        batch = files[i:i+batch_size]
        print(f"🌀 Processing batch {i // batch_size + 1} with {len(batch)} file(s)...")

        for file in batch:
            path = file.get("path")
            content = file.get("content")

            if not path or content is None:
                failed_files.append((path or "<missing>", "Missing path or content"))
                continue

            full_path = PROJECT_ROOT / path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            for attempt in range(1, retry_limit + 2):  # 1 original + N retries
                try:
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    success_count += 1
                    break  # Exit retry loop on success
                except Exception as e:
                    print(f"❌ Attempt {attempt} failed for {path}: {e}")
                    await asyncio.sleep(0.1)  # Small delay before retry
                    if attempt == retry_limit + 1:
                        failed_files.append((path, str(e)))

            await asyncio.sleep(0.05)  # Light delay to reduce overload

    # 📋 Summary message
    summary_lines = [
        f"✅ Successfully wrote {success_count}/{total_files} file(s) to ~/generated-framework."
    ]
    if failed_files:
        summary_lines.append(f"❌ {len(failed_files)} file(s) failed:")
        for path, err in failed_files:
            summary_lines.append(f"- {path}: {err}")

    return TextContent(type="text", text="\n".join(summary_lines))
