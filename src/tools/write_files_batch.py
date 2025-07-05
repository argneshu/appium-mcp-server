import asyncio
import pathlib
from mcp.types import TextContent

PROJECT_ROOT = pathlib.Path.home() / "generated-framework"

async def handle_write_files_batch(arguments: dict) -> TextContent:
    """
    Write multiple files in one call.

    arguments = {
        "files": [
            {"path": "src/test/java/com/example/pages/HomePage.java",
             "content": "public class HomePage {}"},
            ...
        ]
    }
    """
    files = arguments.get("files", [])
    if not isinstance(files, list) or not files:
        return TextContent(
            type="text",
            text="⚠️ No valid 'files' array provided."
        )

    success_count = 0
    for file in files:
        try:
            path = file.get("path")
            content = file.get("content", "")
            if not path:
                raise ValueError("Missing 'path' in file entry")

            full_path = PROJECT_ROOT / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            success_count += 1

            # Optional delay (tune or remove as needed)
            await asyncio.sleep(0.1)

        except Exception as e:
            return TextContent(
                type="text",
                text=f"❌ Failed to write `{file.get('path', '?')}`: {str(e)}"
            )

    return TextContent(
        type="text",
        text=f"✅ Successfully wrote {success_count} file(s) to ~/generated-framework"
    )
