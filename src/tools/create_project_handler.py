import pathlib
from datetime import date
from mcp.types import TextContent

# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

def infer_package_from_project(project_name: str) -> str:
    """
    Turn 'video-e2e-suite' → 'com.video.e2e.suite'.
    Fallback is 'com.example.app'.
    """
    parts = [p for p in project_name.replace("-", "_").split("_") if p.isidentifier()]
    return f"com.{'.'.join(parts)}" if parts else "com.example.app"

def create_maven_dirs(base: pathlib.Path, pkg: str) -> dict:
    pkg_path = pathlib.Path(*pkg.split("."))
    java_root = base / "src/test/java" / pkg_path
    resources_root = base / "src/test/resources"
    subdirs = [
        java_root / "base",
        java_root / "pages",
        java_root / "tests",
        java_root / "utils",
        resources_root,
    ]
    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)
    return {"pkg_path": pkg_path, "java_root": java_root, "resources_root": resources_root}

def write(path: pathlib.Path, content: str, created: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    created.append(str(path))

# ────────────────────────────────────────────────────────────
# Main handler
# ────────────────────────────────────────────────────────────

def handle_create_project_tool(args: dict) -> list[TextContent]:
    project_name: str = args["project_name"]                       # required
    package: str = args.get("package") or infer_package_from_project(project_name)
    pages: list[str] = args.get("pages", ["SamplePage"])
    tests: list[str] = args.get("tests", ["SampleTest"])

    project_root = pathlib.Path.home() / "generated-framework" / project_name
    if project_root.exists():
        import shutil; shutil.rmtree(project_root)                 # start fresh

    paths = create_maven_dirs(project_root, package)
    java_root, resources_root = paths["java_root"], paths["resources_root"]
    pkg_decl = package

    created: list[str] = []

    # ───── pom.xml ─────
    write(project_root / "pom.xml", f"""
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{package}</groupId>
  <artifactId>{project_name}</artifactId>
  <version>1.0-SNAPSHOT</version>
  <name>{project_name}</name>
  <description>Appium tests generated {date.today()}</description>

  <dependencies>
    <dependency>
      <groupId>io.appium</groupId>
      <artifactId>java-client</artifactId>
      <version>9.2.0</version>
    </dependency>
    <dependency>
      <groupId>org.testng</groupId>
      <artifactId>testng</artifactId>
      <version>7.10.2</version>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.2.5</version>
        <configuration>
          <suiteXmlFiles>
            <suiteXmlFile>src/test/resources/testng.xml</suiteXmlFile>
          </suiteXmlFiles>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
""", created)

    # ───── Base classes ─────
    write(java_root / "base" / "BaseTest.java", f"""
package {pkg_decl}.base;

import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.remote.DesiredCapabilities;
import org.testng.annotations.*;

import java.net.URL;

public class BaseTest {{
    protected AppiumDriver driver;

    @BeforeClass
    public void setUp() throws Exception {{
        DesiredCapabilities caps = new DesiredCapabilities();
        caps.setCapability("platformName", "Android");  // default; override per test
        driver = new AppiumDriver(new URL("http://localhost:4723/wd/hub"), caps);
    }}

    @AfterClass
    public void tearDown() {{
        if (driver != null) driver.quit();
    }}
}}
""", created)

    write(java_root / "pages" / "BasePage.java", f"""
package {pkg_decl}.pages;

import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.support.PageFactory;

public abstract class BasePage {{
    protected AppiumDriver driver;
    public BasePage(AppiumDriver driver) {{
        this.driver = driver;
        PageFactory.initElements(driver, this);
    }}
}}
""", created)

    # ───── Dynamic Page Objects ─────
    for page in pages:
        write(java_root / "pages" / f"{page}.java", f"""
package {pkg_decl}.pages;

public class {page} extends BasePage {{
    public {page}(io.appium.java_client.AppiumDriver driver) {{
        super(driver);
    }}
    // TODO: define page elements
}}
""", created)

    # ───── Dynamic Tests ─────
    test_class_lines = []
    for test in tests:
        write(java_root / "tests" / f"{test}.java", f"""
package {pkg_decl}.tests;

import {pkg_decl}.base.BaseTest;
import org.testng.annotations.Test;

public class {test} extends BaseTest {{

    @Test
    public void run() {{
        System.out.println("{test} executed.");
        // TODO: add assertions
    }}
}}
""", created)
        test_class_lines.append(f'      <class name="{pkg_decl}.tests.{test}"/>')

    # ───── Resources ─────
    write(resources_root / "config.properties", "# key=value", created)
    write(resources_root / "log4j2.xml", "<Configuration status=\"WARN\"/>", created)
    write(resources_root / "testng.xml", f"""<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="{project_name}">
  <test name="AllTests">
{chr(10).join(test_class_lines)}
  </test>
</suite>
""", created)

    return [
        TextContent(
            type="text",
            text="✅ Project created:\n" + "\n".join(created)
        )
    ]
