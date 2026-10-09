"""Build script to generate a standalone Vercel-ready WebAssembly (stlite) bundle."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
PUBLIC_DIR = ROOT / "public"


def collect_files() -> dict[str, str]:
    """Collect all python modules and data files required to run the dashboard."""
    files_to_bundle: dict[str, str] = {}

    # 1. Main dashboard
    app_path = ROOT / "dashboard" / "app.py"
    files_to_bundle["dashboard/app.py"] = app_path.read_text(encoding="utf-8")

    # 2. Source packages (both in src/ecofiber_ai and ecofiber_ai)
    src_dir = ROOT / "src" / "ecofiber_ai"
    for py_file in src_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        files_to_bundle[f"src/ecofiber_ai/{py_file.name}"] = content
        files_to_bundle[f"ecofiber_ai/{py_file.name}"] = content

    # 3. Data files
    data_files = [
        ROOT / "data" / "raw" / "literature" / "source_register.csv",
        ROOT / "data" / "raw" / "literature" / "literature_observations.csv",
        ROOT / "data" / "templates" / "experimental_observations_template.csv",
        ROOT / "data" / "templates" / "experimental_test_log_template.csv",
    ]

    for df in data_files:
        if df.is_file():
            rel_path = df.relative_to(ROOT).as_posix()
            files_to_bundle[rel_path] = df.read_text(encoding="utf-8")

    return files_to_bundle


def generate_index_html(files: dict[str, str]) -> str:
    """Generate the static HTML page loading stlite."""
    files_json = json.dumps(files, indent=2)

    html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
    <title>EcoFiber AI — Sustainable Bio-Composites</title>
    <meta name="description" content="AI-Powered Prediction, Evidence Audit & Sustainable Formulation Optimization for Ipomoea carnea Bio-Composites" />
    <link rel="icon" href="https://raw.githubusercontent.com/feathericons/feather/master/icons/feather.svg" type="image/svg+xml" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/mountable@0.73.1/build/stlite.css" />
    <style>
      body {{
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      }}
      #loading-screen {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%);
        color: white;
        z-index: 9999;
        transition: opacity 0.5s ease-out;
      }}
      .spinner {{
        width: 50px;
        height: 50px;
        border: 5px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: white;
        animation: spin 1s ease-in-out infinite;
        margin-bottom: 20px;
      }}
      @keyframes spin {{
        to {{ transform: rotate(360deg); }}
      }}
      h1 {{
        margin: 0 0 10px 0;
        font-size: 2rem;
        font-weight: 700;
      }}
      p {{
        margin: 0;
        font-size: 1.1rem;
        opacity: 0.9;
      }}
    </style>
  </head>
  <body>
    <div id="loading-screen">
      <div class="spinner"></div>
      <h1>🌿 EcoFiber AI</h1>
      <p>Initializing WebAssembly & Pyodide Python Environment...</p>
    </div>
    <div id="root"></div>

    <script src="https://cdn.jsdelivr.net/npm/@stlite/mountable@0.73.1/build/stlite.js"></script>
    <script>
      const files = {files_json};

      stlite.mount({{
        requirements: ["pandas", "numpy", "scikit-learn", "plotly", "matplotlib"],
        entrypoint: "dashboard/app.py",
        files: files,
      }}, document.getElementById("root")).then(() => {{
        const loading = document.getElementById("loading-screen");
        if (loading) {{
          loading.style.opacity = "0";
          setTimeout(() => loading.remove(), 500);
        }}
      }});
    </script>
  </body>
</html>
"""
    return html


def build():
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    files = collect_files()
    html_content = generate_index_html(files)
    output_path = PUBLIC_DIR / "index.html"
    output_path.write_text(html_content, encoding="utf-8")
    print(f"Successfully generated Vercel WebAssembly bundle at: {output_path}")
    print(f"Bundled {len(files)} files into Pyodide virtual filesystem.")


if __name__ == "__main__":
    build()
