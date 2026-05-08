# Cairo Smart City Frontend

This is the React-based frontend for the Cairo Smart City Transportation Network Optimization project.

## Tech Stack
- **Framework:** React + Vite
- **Styling:** Tailwind CSS + Lucide Icons
- **Maps:** React-Leaflet (OpenStreetMap)
- **Design System:** Custom premium design with Shadcn-like variables.

## How to Run

1. **Prerequisites:** Ensure you have [Node.js](https://nodejs.org/) installed.
2. **Install Dependencies:**
   ```bash
   cd frontend
   npm install
   ```
3. **Start Development Server:**
   ```bash
   npm run dev
   ```
4. **Backend Connection:**
   Ensure the Python FastAPI backend is running (typically on `http://localhost:8000`).

## Project Structure
- `src/App.jsx`: Main dashboard layout with Sidebar and Map container.
- `src/components/TransportationMap.jsx`: Interactive Leaflet map implementation.
- `src/index.css`: Tailwind configuration and global styles.
