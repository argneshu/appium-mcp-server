import sys
import asyncio
import pathlib
from mcp.types import TextContent

PROJECT_ROOT = pathlib.Path.home() / "generated-framework"

async def handle_write_files_batch(arguments: dict) -> TextContent:
    """
    Write multiple files at once.
    arguments = {"files": [{"path": "...", "content": "..."}, ...]}
    """
    files = arguments.get("files", [])
    if not files:
        return TextContent(
            type="text",
            text="⚠️ No files provided to write."
        )

    success_count = 0
    total_files = len(files)

    # Log to STDERR so MCP stdout stays JSON‑only
    print(f"🌀 write_files_batch received {total_files} file(s)", file=sys.stderr)

    for file in files:
        path = file.get("path")
        content = file.get("content", "")

        if not path:
            print("⚠️ Skipping entry with missing path", file=sys.stderr)
            continue

        full_path = PROJECT_ROOT / path
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            success_count += 1
            print(f"✅ Wrote: {path}", file=sys.stderr)

        except Exception as e:
            print(f"❌ Failed to write {path}: {e}", file=sys.stderr)
            return TextContent(
                type="text",
                text=f"❌ Failed to write file '{path}': {e}"
            )

        # Optional throttle to avoid flooding transport
        await asyncio.sleep(0.1)

    return TextContent(
        type="text",
        text=f"✅ Successfully wrote {success_count}/{total_files} file(s) to ~/generated-framework"
    )
