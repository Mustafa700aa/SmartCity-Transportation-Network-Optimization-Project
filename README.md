# Cairo Smart City: Transportation Network Optimization Platform

## 1. Project Overview & Objectives

The Cairo Smart City Transportation Network Optimization Platform is an enterprise-grade decision support system engineered to alleviate urban congestion and optimize infrastructure utilization within the Greater Cairo metropolitan area. By integrating advanced Graph Theory, Dynamic Programming, and Greedy algorithmic paradigms, the platform provides actionable, data-driven insights for city planners and traffic control centers. The primary objective is to deliver optimal routing, automated infrastructure expansion planning, and budget-constrained maintenance scheduling through a highly decoupled, scalable, and mathematically rigorous architecture.

## 2. Core Capabilities

The platform's computational engine is segmented into four primary algorithmic families:

*   **Multi-Strategy Routing Engine**: A real-time pathfinding module utilizing Dijkstra's algorithm and A* search (with a Euclidean heuristic). The engine dynamically calculates edge weights by alternating between two strategies: a physical traffic model based on the Bureau of Public Roads (BPR) function, and a predictive Machine Learning fallback utilizing a `HistGradientBoostingRegressor` to estimate travel times under complex non-linear conditions.
*   **Infrastructure Expansion**: An automated network growth planning module that employs Kruskal’s Minimum Spanning Tree (MST) algorithm. This ensures 100% connectivity across all defined urban nodes while guaranteeing the lowest possible aggregate construction overhead.
*   **Maintenance Optimization**: A 0/1 Knapsack (Dynamic Programming) solver designed to select the globally optimal subset of road repairs. Discretization scaling and explicit `math.ceil` boundaries are strictly applied during weight calculations to prevent floating-point underestimation, ensuring the solution never violates strict budget constraints.
*   **Traffic Flow Control**: An adaptive signal timing module leveraging greedy optimization to maximize throughput at critical intersections. This is coupled with an Emergency Preemption System that guarantees unhindered routing for emergency vehicles (e.g., ambulances, fire engines) through dynamic signal overrides.

## 3. System Architecture

The platform is designed adhering strictly to Clean Architecture and SOLID principles, enforcing a unidirectional dependency rule that isolates the core algorithmic logic from external frameworks, databases, and UI components.

*   **Entities/Domain Layer**: Contains pure Python data structures representing the physical transportation network, including Nodes, Edges, and Optimization Result schemas.
*   **Core Engine Layer**: Manages the central graph representation and state. It implements the Strategy Pattern via the `WeightEngine`, allowing seamless runtime swapping between the BPR physical model and the ML predictive model.
*   **Algorithms Layer**: Houses the decoupled, stateless implementations of the pathfinding algorithms (Dijkstra, A*), DP solvers (0/1 Knapsack), and MST logic.
*   **Infrastructure Layer**: Handles data persistence, CSV loading/parsing, external API integrations, and the instantiation of the Machine Learning models.
*   **Presentation/API Layer**: Provides a high-performance RESTful API gateway using FastAPI, and a modern, responsive single-page application dashboard built with React.

## 4. Mathematical Foundation

### The Bureau of Public Roads (BPR) Congestion Model
The routing engine calculates the congested travel time (cost) of a road segment utilizing the BPR formula:

$$T = T_0 \times \left(1 + \alpha \times \left(\frac{V}{C}\right)^\beta\right)$$

Where:
*   $T$: Congested travel time.
*   $T_0$: Free-flow travel time.
*   $V$: Traffic volume.
*   $C$: Road segment capacity.
*   $\alpha, \beta$: Standard calibration parameters (typically $\alpha=0.15, \beta=4$).

### Maintenance Optimization (0/1 Knapsack)
The maintenance module identifies the optimal set of road repairs by maximizing the total traffic benefit without exceeding the maximum financial budget. The objective function is defined as:

$$\max \sum_{i=1}^{n} B_i x_i \quad \text{subject to} \quad \sum_{i=1}^{n} C_i x_i \leq \text{Budget}$$

Where:
*   $B_i$: Traffic benefit (throughput restored) of repairing road segment $i$.
*   $C_i$: Financial cost of repairing road segment $i$.
*   $x_i \in \{0, 1\}$: Decision variable indicating whether road segment $i$ is selected for repair.

## 5. Technology Stack

| Component | Technologies |
| :--- | :--- |
| **Backend** | Python 3.11, FastAPI, Pydantic, Scikit-learn, Pytest |
| **Frontend** | React 18, Vite, Tailwind CSS, Shadcn UI, Leaflet.js |
| **DevOps** | Docker, Docker Compose |

## 6. Installation & Setup

### Backend Setup
1.  Navigate to the project root directory.
2.  Install the required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Launch the FastAPI server:
    ```bash
    python -m uvicorn api:app --reload --port 8000
    ```

### Frontend Setup
1.  Navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```
2.  Install the necessary Node.js packages:
    ```bash
    npm install
    ```
3.  Start the development server:
    ```bash
    npm run dev
    ```

## 7. Testing & Quality Assurance

The platform is fortified by a comprehensive automated QA suite to guarantee algorithmic correctness and system stability. Key testing areas include:

*   **A* Admissibility**: Mathematical verification that the Euclidean heuristic never overestimates the actual shortest path cost.
*   **MST Tree Properties**: Validation of canonical edge identification to ensure acyclic structures and optimal minimum cost configurations.
*   **DP Constraint Boundaries**: Stress testing the 0/1 Knapsack implementation to verify that boundary conditions, particularly regarding discretization and budget limits, are strictly maintained.


