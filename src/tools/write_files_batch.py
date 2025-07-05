import asyncio
import pathlib
from mcp.types import TextContent

PROJECT_ROOT = pathlib.Path.home() / "generated-framework"

async def handle_write_files_batch(arguments: dict) -> TextContent:
    files = arguments.get("files", [])

    if not files:
        return TextContent(text="⚠️ No files provided to write.")

    for file in files:
        try:
            path = file["path"]
            content = file["content"]
            full_path = PROJECT_ROOT / path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w") as f:
                f.write(content)

            # Optional delay to reduce overload if too many files
            await asyncio.sleep(0.1)
        except Exception as e:
            return TextContent(
                text=f"❌ Failed to write file `{file.get('path', '?')}`: {str(e)}"
            )

    return TextContent(
        text=f"✅ Successfully wrote {len(files)} file(s) to ~/generated-framework"
    )

