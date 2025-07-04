import os
import pathlib
from mcp.types import TextContent

def create_maven_project_structure(base_path: pathlib.Path, package_name: str):
    package_path = package_name.replace('.', '/')
    java_base = base_path / "src/test/java" / package_path
    resources_base = base_path / "src/test/resources"
    subdirs = [
        java_base / "base",
        java_base / "pages",
        java_base / "tests",
        java_base / "utils",
        resources_base,
    ]
    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)

    return {
        "base_path": str(base_path),
        "package_path": package_path,
        "subdirs": [str(d) for d in subdirs]
    }

def handle_create_project_tool(arguments: dict) -> list[TextContent]:
    project_name = arguments.get("project_name", "youtube-appium-tests")
    package_name = arguments.get("package_name", "com.youtube.automation")

    project_root = pathlib.Path.home() / "generated-framework" / project_name
    result = create_maven_project_structure(project_root, package_name)

    # Basic files
    files_to_write = {
        project_root / "pom.xml": f"""<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>{package_name}</groupId>
  <artifactId>{project_name}</artifactId>
  <version>1.0-SNAPSHOT</version>
</project>""",
        project_root / "src/test/resources/config.properties": "url=https://youtube.com\nplatform=iOS",
        project_root / "src/test/resources/testng.xml": """<suite name="YouTube Test Suite">
  <test name="YouTube Tests">
    <classes>
      <class name="com.youtube.automation.tests.YouTubeContentNavigationTest"/>
    </classes>
  </test>
</suite>""",
        project_root / f"src/test/java/{result['package_path']}/tests/YouTubeContentNavigationTest.java": f"""package {package_name}.tests;

import org.testng.annotations.Test;

public class YouTubeContentNavigationTest {{
    @Test
    public void testNavigation() {{
        System.out.println("Test navigating YouTube app.");
    }}
}}""",
    }

    for path, content in files_to_write.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    return [
        TextContent(
            type="text",
            text=f"✅ Project `{project_name}` created at: {project_root}"
        )
    ]

