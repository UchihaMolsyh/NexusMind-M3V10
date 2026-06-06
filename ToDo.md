# Project Aegis - Open-Source Version Workspace TODO

## [Phase 1: Core Performance Triage & Fixes]
- [ ] Implement `bunfig.toml` directory exclusions (`**/database/**`, `**/*.md`, `**/wiki/**`) to break the reactive hot-reload infinity loop.
- [ ] Inject JavaScriptCore synchronous heap compaction (`Bun.gc(true)`) inside `src/ui/tauri/canvas/state_manager.js` to fix the 20GB RAM memory leak.
- [ ] Deploy isolated Byte-Pair Encoded Token Translation wrapper inside `src/core/router.py` to stop Qwen2.5-0.5B-Instruct instruction vocabulary bleed.
- [ ] Integrate explicit `DRAFT_TEMPLATE` parsing to force the 0.5B model to handle structural validation check blocks safely.

## [Phase 2: Local Core Runtimes & Acceleration Engine]
- [ ] Bind `llama.cpp` using local Python bindings (`llama-cpp-python`) into `src/llm/engine.py` to manage model parameters.
- [ ] Configure `llama.cpp` dynamic KV-cache shifting to safely run `DeepSeek-R1-Distill-Qwen-14B (GGUF)` 4-bit quant files locally.
- [ ] Inject `MatrixCore` custom zero-dependency linear algebra module into `src/tools/math/math_solver.py` for micro-simulations.
- [ ] Compile Andrej Karpathy's `llm.c` wrapper as a raw C-extension binary for high-speed local text pattern evaluation loops.
- [ ] Integrate Karpathy's `minbpe` tokenizer wrapper into `src/llm/karpathy_core/minbpe_tokenizer.py` for light context compression checks.
- [ ] Set up the `Bun` JavaScript runtime engine inside `src/ui/tauri/package.json` to handle active client-side operations.

## [Phase 3: High-Speed Embedded Databases & Vector Pipelines]
- [ ] Establish local relational storage structures by initializing the primary column-oriented `DuckDB` backend database layer.
- [ ] Deploy the serverless `SQLite` transaction database to run secure, persistent conversation logs.
- [ ] Configure local `Sentence-Transformers` CPU embedding models to convert incoming documents into vector formats for zero cost.
- [ ] Program `RankBM25` keyword-lexical search layers to run a hybrid checking system alongside `Meta FAISS` vector similarity matching.
- [ ] Mount `FlashRank` document re-ranking loops on CPU to prune raw matching chunks down to the 3 most relevant data cards.
- [ ] Structure local data transaction operations cleanly using open-source `SQLAlchemy` database routing properties.
- [ ] Connect the `Watchdog` file-system listener to monitor the Markdown directory and update vector indices on modification.

## [Phase 4: Open Spatial OSINT & Telemetry Gathering Hub]
- [ ] Build the OpenStreetMap asynchronous spatial bounding box data extraction script using the free `Overpass API`.
- [ ] Script the `aiohttp` parallel web-scraping loop to parse crowdsourced aviation transponder parameters via the public `ADS-B Exchange API`.
- [ ] Integrate the non-profit `OpenSky Network API` data tracking endpoint as a secondary flight-vector cross-reference fallback.
- [ ] Deploy `HTTPX` as the concurrent data collection client alongside `BeautifulSoup4` to scrape data layouts without interface lag.
- [ ] Wire the backend WebSocket server (`Uvicorn` / `Gunicorn`) to stream live geospatial telemetry data frames to the frontend at 60 FPS.
- [ ] Build the local hardware metrology worker using `psutil` to stream real-time CPU thermal bounds to the UI dashboard.
- [ ] Integrate `Feedparser` background worker daemons to read incoming RSS technology news streams and software release logs for $0.

## [Phase 5: Code Quality Verification & Multi-Thread Analytics]
- [ ] Mount `Ruff` and `Black` automation hooks into the local code-generation folder to enforce clean syntax formats.
- [ ] Configure `Flake8` lint checking rules to measure structural complexity indices on self-generated scripts.
- [ ] Import `Pandas` and `Scipy` matrix processing tools to analyze high-volume data streams inside the math solver directory.
- [ ] Inject `Sympy` symbolic computation blocks to handle step-by-step formula derivations for Physics and Math Olympiad sheets.
- [ ] Integrate `Joblib` transparent disk-caching to store intermediate embedding vectors and prevent redundant recalculations.
- [ ] Deploy `Fastparquet` and `PyArrow` to compress historical log pools into highly condensed binary column files on disk.
- [ ] Set up `Openpyxl` standard file readers to parse incoming spreadsheets into clean Pydantic object profiles.

## [Phase 6: 2.5D Rendering Canvas & Interface Layouts]
- [ ] Build the core 3D application window viewport utilizing `Three.js` hardware-accelerated graphic structures.
- [ ] Layer `PixiJS` WebGL engines beneath the main canvas to render thousands of moving log lines and coordinate paths at 60 FPS.
- [ ] Configure `Zustand` as the 1KB state controller to coordinate data states across the user interface layout.
- [ ] Map out the `React Flow` node workspace to visually render task milestone nodes on the UI dashboard.
- [ ] Connect `Cytoscape.js` topological layouts to mathematically organize network graphs without overlapping nodes.
- [ ] Deploy the `CesiumJS` 3D virtual globe layer to plot flight tracking vectors dynamically over regional map projections.
- [ ] Configure the 2D `Leaflet` viewport as a fast fallback canvas layout to plot spatial tracking coordinates smoothly.
- [ ] Structure data analytic displays using `D3.js` vector charts to track real-time resource footprints.
- [ ] Install components from `Shadcn UI` and `Lucide React` vector asset directories to style interface trays and action icons.
