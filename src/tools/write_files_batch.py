import asyncio
import pathlib
from mcp.types import TextContent

PROJECT_ROOT = pathlib.Path.home() / "generated-framework"

async def handle_write_files_batch(arguments: dict) -> TextContent:
    """
    Write multiple files at once.
    Expected arguments payload:
    {
      "files": [
        {"path": "relative/path/File.java", "content": "..."},
        ...
      ]
    }
    """
    files = arguments.get("files", [])
    if not files:
        return TextContent(
            type="text",
            text="⚠️ No files provided to write."
        )

    success_count = 0
    for file in files:
        try:
            path = file.get("path")
            content = file.get("content", "")

            if not path:
                continue  # skip invalid entry

            full_path = PROJECT_ROOT / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            success_count += 1

            # Optional delay to reduce rapid‑fire load on the transport
            await asyncio.sleep(0.1)

        except Exception as e:
            return TextContent(
                type="text",
                text=f"❌ Failed to write file '{path}': {e}"
            )

    return TextContent(
        type="text",
        text=f"✅ Successfully wrote {success_count}/{len(files)} file(s) to ~/generated-framework"
    )
