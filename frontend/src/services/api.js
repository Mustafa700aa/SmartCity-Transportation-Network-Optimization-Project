const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const transportApi = {
  /**
   * Fetch all nodes and edges from the graph
   */
  getGraph: async () => {
    const response = await fetch(`${API_BASE_URL}/api/graph`);
    if (!response.ok) throw new Error('Failed to fetch graph data');
    return response.json();
  },

  /**
   * Calculate route using Dijkstra
   */
  getRoute: async (params) => {
    const response = await fetch(`${API_BASE_URL}/api/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!response.ok) throw new Error('Failed to calculate route');
    return response.json();
  },

  /**
   * Calculate route using A*
   */
  getAStar: async (params) => {
    const response = await fetch(`${API_BASE_URL}/api/astar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!response.ok) throw new Error('Failed to calculate A* route');
    return response.json();
  },

  /**
   * Get Minimum Spanning Tree
   */
  getMST: async () => {
    const response = await fetch(`${API_BASE_URL}/api/mst`);
    if (!response.ok) throw new Error('Failed to fetch MST data');
    return response.json();
  },

  /**
   * Run 0/1 Knapsack road maintenance optimizer
   * @param {number} budget - Maximum budget in Million EGP
   */
  getMaintenance: async (budget) => {
    const response = await fetch(`${API_BASE_URL}/api/maintenance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ budget }),
    });
    if (!response.ok) throw new Error('Failed to run maintenance optimizer');
    return response.json();
  },
};
