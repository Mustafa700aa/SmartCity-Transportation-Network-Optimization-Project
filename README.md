# Graph Integration & Dynamic Weighting Engine

Quick guide for running the graph construction and visualization flow from CSV files.

## 1) Requirements

- Python 3.10+ (3.11+ recommended)
- `matplotlib`

Install requirements:

```bash
pip install matplotlib
```

## 2) Required Data Files (must exist in `--data-dir`)

- `Neighborhoods.csv`
- `Facilities.csv`
- `Existing_Roads.csv`
- `Potential_Roads.csv`
- `Traffic_Flow.csv`
- `Transport_Demand.csv`
- `Bus_Routes.csv`
- `Metro_Lines.csv`

## 3) Run

From inside the project folder:

```bash
python3 transport_graph_local_dataclasses.py --data-dir "."
```

Or with an absolute path:

```bash
python3 transport_graph_local_dataclasses.py --data-dir "/absolute/path/to/Graph Integration & Dynamic Weighting Engine"
```

## 3.1) Terminal Prompt (Copy/Paste)

```bash
cd "/algorithmProjectTasks/Graph Integration & Dynamic Weighting Engine"
python3 transport_graph_local_dataclasses.py --data-dir "."
```

## 4) CLI Options

- `--hide-potential`: hide the potential roads layer.
- `--hide-labels`: hide node labels/IDs in plots.
- `--annotate {all,facilities,neighborhoods}`:
  - `all`: show all node labels
  - `facilities`: show facility labels only
  - `neighborhoods`: show neighborhood labels only

Example:

```bash
python3 transport_graph_local_dataclasses.py --data-dir "." --hide-potential --annotate facilities
```

## 5) Expected Output

- Prints a `Graph summary` in terminal (nodes, routes, edges).
- Opens 5 plot windows:
  - 1 combined graph
  - 4 path-highlight graphs (existing/potential/bus/metro)
- Each window includes:
  - graph visualization
  - layer legend
  - numeric stats box (nodes/routes/edges + total buses)

## 6) Troubleshooting

- If `--data-dir` is missing: provide it explicitly in the command.
- If windows do not appear on a headless server: run on a machine with GUI support.
- `matplotlib cache` warnings are usually non-blocking.

## 7) Main Script

- `transport_graph_local_dataclasses.py`
