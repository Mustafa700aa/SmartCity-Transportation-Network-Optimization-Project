import React, { useState, useEffect } from 'react';
import {
  Route, Construction, Wrench, Settings,
  ChevronRight, Zap, Building2, Bus, TrainFront,
  Search, Loader2, AlertCircle, Map as MapIcon,
  TrendingUp, DollarSign, CheckCircle2, XCircle,
  BarChart3,
} from 'lucide-react';
import TransportationMap from './components/TransportationMap';
import { transportApi } from './services/api';

// ─── tiny helpers ───────────────────────────────────────────────────────────

function StatBadge({ label, value, sub, color = 'blue' }) {
  const colors = {
    blue:   'bg-blue-50   border-blue-100   text-blue-700',
    orange: 'bg-orange-50 border-orange-100 text-orange-700',
    amber:  'bg-amber-50  border-amber-100  text-amber-700',
    emerald:'bg-emerald-50 border-emerald-100 text-emerald-700',
    red:    'bg-red-50    border-red-100    text-red-700',
  };
  return (
    <div className={`flex-1 p-4 rounded-2xl border ${colors[color]}`}>
      <p className="text-[9px] font-black uppercase tracking-widest opacity-60 mb-1">{label}</p>
      <p className="text-xl font-black leading-none">{value}</p>
      {sub && <p className="text-[10px] font-bold opacity-60 mt-0.5">{sub}</p>}
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-1 pt-2">
      {children}
    </p>
  );
}

// ─── main App ───────────────────────────────────────────────────────────────

export default function App() {
  // ── state ──
  const [activeTab, setActiveTab]     = useState('routing');
  const [nodes,     setNodes]         = useState([]);
  const [appLoading, setAppLoading]   = useState(true);
  const [error,     setError]         = useState(null);

  // routing
  const [routeParams, setRouteParams] = useState({
    start_node: '', end_node: '', time_of_day: 'morning', weight_mode: 'bpr',
  });
  const [useAstar,     setUseAstar]     = useState(false); // FIX-2: Emergency mode toggle
  const [routeResult,  setRouteResult]  = useState(null);
  const [routeLoading, setRouteLoading] = useState(false);

  // mst
  const [mstResult,  setMstResult]  = useState(null);
  const [mstLoading, setMstLoading] = useState(false);

  // maintenance
  const [budget,       setBudget]       = useState('50');
  const [maintResult,  setMaintResult]  = useState(null);
  const [maintLoading, setMaintLoading] = useState(false);

  // ── init ──
  useEffect(() => {
    transportApi.getGraph()
      .then(d => { setNodes(d.nodes); setAppLoading(false); })
      .catch(() => {
        setError('Cannot connect to the Cairo API (port 8000). Start the FastAPI backend first.');
        setAppLoading(false);
      });
  }, []);

  // FIX-1: Clear ALL map layers whenever the active tab changes.
  // This prevents stale polylines from a previous operation bleeding
  // into the new tab's visual context.
  useEffect(() => {
    setRouteResult(null);
    setMstResult(null);
    setMaintResult(null);
  }, [activeTab]);

  // ── helpers to clear sibling results ──
  // NOTE: Tab-level clearing is now handled by the useEffect above.
  // This helper clears siblings within a single tab's actions.
  const clearSiblings = (current) => {
    if (current !== 'route') setRouteResult(null);
    if (current !== 'mst')   setMstResult(null);
    if (current !== 'maint') setMaintResult(null);
  };

  // ── actions ──
  const handleRoute = async () => {
    if (!routeParams.start_node || !routeParams.end_node) return;
    clearSiblings('route');
    setRouteLoading(true);
    try {
      const res = useAstar
        ? await transportApi.getAStar(routeParams)
        : await transportApi.getRoute(routeParams);
      setRouteResult(res);
    } catch (e) { setError(e.message); }
    finally { setRouteLoading(false); }
  };

  const handleMST = async () => {
    clearSiblings('mst');
    setMstLoading(true);
    try { setMstResult(await transportApi.getMST()); }
    catch (e) { setError(e.message); }
    finally { setMstLoading(false); }
  };

  const handleMaintenance = async () => {
    const b = parseFloat(budget);
    if (!b || b <= 0) { setError('Please enter a valid budget > 0'); return; }
    clearSiblings('maint');
    setMaintLoading(true);
    try { setMaintResult(await transportApi.getMaintenance(b)); }
    catch (e) { setError(e.message); }
    finally { setMaintLoading(false); }
  };

  // ── derived stats ──
  const selectedRoads  = (maintResult?.candidates || []).filter(c => c.selected);
  const criticalRoads  = selectedRoads.filter(c => c.condition < 5).length;

  // ── tabs config ──
  const tabs = [
    { id: 'routing',     name: 'Routing',     short: 'Route', icon: Route,        color: 'text-blue-500' },
    { id: 'mst',         name: 'MST',         short: 'MST',   icon: Construction, color: 'text-orange-500' },
    { id: 'maintenance', name: 'Maintenance', short: 'DP',    icon: Wrench,       color: 'text-amber-500' },
  ];

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen w-full bg-slate-100 overflow-hidden">

      {/* ═══════════════ SIDEBAR ═══════════════ */}
      <aside className="w-[360px] shrink-0 bg-white border-r border-slate-200 flex flex-col shadow-2xl z-20">

        {/* Header */}
        <div className="px-8 pt-8 pb-6 border-b border-slate-100">
          <div className="flex items-center gap-3 mb-1">
            <div className="bg-blue-50 p-2 rounded-xl">
              <Zap className="w-5 h-5 text-blue-500" />
            </div>
            <h1 className="text-xl font-black text-slate-900 tracking-tight">
              Cairo <span className="text-blue-500">SmartCity</span>
            </h1>
          </div>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-12">
            Optimization Dashboard
          </p>
        </div>

        {/* Tab strip */}
        <div className="flex p-3 gap-1.5 bg-slate-50 border-b border-slate-100">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex-1 flex flex-col items-center gap-1 py-3 px-2 rounded-xl text-center transition-all duration-150 ${
                activeTab === t.id
                  ? 'bg-white shadow-md ring-1 ring-slate-200 text-slate-900'
                  : 'text-slate-400 hover:text-slate-600 hover:bg-white/60'
              }`}
            >
              <t.icon className={`w-4 h-4 ${activeTab === t.id ? t.color : ''}`} />
              <span className="text-[9px] font-black uppercase tracking-tight">{t.short}</span>
            </button>
          ))}
        </div>

        {/* ── Panel content ── */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">

          {/* ── ROUTING ── */}
          {activeTab === 'routing' && (
            <>
              <SectionLabel>Find Optimal Route</SectionLabel>

              <div className="space-y-3">
                {/* Start */}
                <div className="space-y-1">
                  <label className="text-[9px] font-black text-slate-400 uppercase ml-0.5">Origin</label>
                  <select
                    value={routeParams.start_node}
                    onChange={e => setRouteParams(p => ({ ...p, start_node: e.target.value }))}
                    className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-200 transition-all"
                  >
                    <option value="">Select origin node...</option>
                    {nodes.map(n => <option key={n.id} value={n.id}>{n.id} – {n.name}</option>)}
                  </select>
                </div>

                {/* End */}
                <div className="space-y-1">
                  <label className="text-[9px] font-black text-slate-400 uppercase ml-0.5">Destination</label>
                  <select
                    value={routeParams.end_node}
                    onChange={e => setRouteParams(p => ({ ...p, end_node: e.target.value }))}
                    className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-200 transition-all"
                  >
                    <option value="">Select destination node...</option>
                    {nodes.map(n => <option key={n.id} value={n.id}>{n.id} – {n.name}</option>)}
                  </select>
                </div>

                {/* Time + Strategy */}
                <div className="flex gap-2">
                  <div className="flex-1 space-y-1">
                    <label className="text-[9px] font-black text-slate-400 uppercase ml-0.5">Period</label>
                    <select
                      value={routeParams.time_of_day}
                      onChange={e => setRouteParams(p => ({ ...p, time_of_day: e.target.value }))}
                      className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-blue-200"
                    >
                      <option value="morning">Morning</option>
                      <option value="afternoon">Afternoon</option>
                      <option value="evening">Evening</option>
                      <option value="night">Night</option>
                    </select>
                  </div>
                  <div className="flex-1 space-y-1">
                    <label className="text-[9px] font-black text-slate-400 uppercase ml-0.5">Strategy</label>
                    <select
                      value={routeParams.weight_mode}
                      onChange={e => setRouteParams(p => ({ ...p, weight_mode: e.target.value }))}
                      className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-blue-200"
                    >
                      <option value="bpr">BPR Model</option>
                      <option value="ml">ML Prediction</option>
                    </select>
                  </div>
                </div>

                {/* Emergency Mode Toggle — FIX-2 */}
                <div
                  className={`flex items-center gap-3 p-3.5 rounded-xl border-2 cursor-pointer select-none transition-all ${
                    useAstar
                      ? 'bg-red-50 border-red-300 text-red-700'
                      : 'bg-slate-50 border-slate-200 text-slate-500'
                  }`}
                  onClick={() => setUseAstar(a => !a)}
                  role="checkbox"
                  aria-checked={useAstar}
                >
                  {/* Toggle pill */}
                  <div className={`relative w-10 h-5 rounded-full transition-colors shrink-0 ${
                    useAstar ? 'bg-red-500' : 'bg-slate-300'
                  }`}>
                    <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${
                      useAstar ? 'left-[22px]' : 'left-0.5'
                    }`} />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-black">
                      {useAstar ? '🚨 Emergency Mode (A*)' : 'Standard Mode (Dijkstra)'}
                    </p>
                    <p className="text-[9px] font-bold opacity-60">
                      {useAstar ? 'Heuristic search — faster for emergency routing' : 'Optimal shortest path guarantee'}
                    </p>
                  </div>
                </div>

                {/* Single Calculate button */}
                <button
                  onClick={handleRoute}
                  disabled={routeLoading || !routeParams.start_node || !routeParams.end_node}
                  className={`w-full py-4 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg disabled:opacity-40 transition-all flex items-center justify-center gap-2 ${
                    useAstar
                      ? 'bg-red-600 text-white hover:bg-red-700 shadow-red-200'
                      : 'bg-slate-900 text-white hover:bg-slate-800'
                  }`}
                >
                  {routeLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {useAstar ? 'Calculate Emergency Route' : 'Calculate Optimal Route'}
                </button>
              </div>

              {/* Route result card */}
              {routeResult?.found && (
                <div className="bg-blue-50 border border-blue-100 rounded-2xl p-5 space-y-4 mt-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-black text-blue-400 uppercase tracking-widest">Route Found</span>
                    <span className="text-[9px] font-black bg-blue-500 text-white px-2 py-0.5 rounded-full uppercase">{routeResult.iterations} nodes explored</span>
                  </div>
                  <div className="flex gap-3">
                    <StatBadge label="Est. Time"  value={`${routeResult.total_time_min.toFixed(1)}`} sub="minutes" color="blue" />
                    <StatBadge label="Distance"   value={`${routeResult.total_dist_km.toFixed(2)}`} sub="km"      color="blue" />
                  </div>
                  <div>
                    <p className="text-[9px] font-black text-slate-400 uppercase mb-2">Path Sequence</p>
                    <div className="flex flex-wrap gap-1 items-center">
                      {routeResult.path.map((p, i) => (
                        <React.Fragment key={`${p}-${i}`}>
                          <span className="text-[10px] font-black text-slate-700 bg-white border border-blue-100 px-2 py-1 rounded-lg">{p}</span>
                          {i < routeResult.path.length - 1 && (
                            <ChevronRight className="w-3 h-3 text-blue-300 shrink-0" />
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              {routeResult && !routeResult.found && (
                <div className="bg-red-50 border border-red-100 rounded-2xl p-4 flex gap-3 items-start">
                  <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-bold text-red-700">No route found</p>
                    <p className="text-xs text-red-400 mt-0.5">{routeResult.error}</p>
                  </div>
                </div>
              )}
            </>
          )}

          {/* ── MST ── */}
          {activeTab === 'mst' && (
            <>
              <SectionLabel>Minimum Road Expansion Plan</SectionLabel>
              <p className="text-xs text-slate-500 leading-relaxed px-0.5">
                Kruskal's algorithm selects the cheapest subset of potential roads that
                fully connects all 25 city nodes while avoiding redundant loops.
              </p>

              <button
                onClick={handleMST}
                disabled={mstLoading}
                className="w-full bg-orange-500 text-white py-4 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg hover:bg-orange-600 disabled:opacity-40 transition-all flex items-center justify-center gap-2 mt-2"
              >
                {mstLoading
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Construction className="w-4 h-4" />}
                Run Kruskal Algorithm
              </button>

              {mstResult && (
                <div className="bg-orange-50 border border-orange-100 rounded-2xl p-5 space-y-4 mt-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-black text-orange-400 uppercase tracking-widest">MST Computed</span>
                    <span className={`text-[9px] font-black px-2 py-0.5 rounded-full uppercase ${
                      mstResult.fully_connected
                        ? 'bg-emerald-500 text-white'
                        : 'bg-red-400 text-white'
                    }`}>
                      {mstResult.fully_connected ? 'Fully Connected' : 'Partial'}
                    </span>
                  </div>
                  <div className="flex gap-3">
                    <StatBadge label="Total Cost" value={`${mstResult.total_cost.toFixed(0)}M`}  sub="EGP"        color="orange" />
                    <StatBadge label="Roads Added" value={mstResult.mst_edges.length} sub="segments" color="orange" />
                  </div>
                  <div className="flex gap-3">
                    <StatBadge label="Components Before" value={mstResult.components_before} color="orange" />
                    <StatBadge label="After MST" value={mstResult.components_after} color="emerald" />
                  </div>
                </div>
              )}
            </>
          )}

          {/* ── MAINTENANCE ── */}
          {activeTab === 'maintenance' && (
            <>
              <SectionLabel>0/1 Knapsack Road Repair</SectionLabel>
              <p className="text-xs text-slate-500 leading-relaxed px-0.5">
                The DP optimizer selects the globally optimal set of roads to repair
                within your budget, maximising total traffic throughput restored.
              </p>

              {/* Budget input */}
              <div className="space-y-1 mt-1">
                <label className="text-[9px] font-black text-slate-400 uppercase ml-0.5">
                  Maximum Budget (Million EGP)
                </label>
                <div className="relative">
                  <DollarSign className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-amber-500" />
                  <input
                    type="number"
                    min="1"
                    step="5"
                    value={budget}
                    onChange={e => setBudget(e.target.value)}
                    placeholder="e.g. 50"
                    className="w-full pl-10 pr-4 py-3.5 bg-amber-50 border-2 border-amber-200 rounded-xl text-sm font-bold text-amber-900 placeholder:text-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-300 transition-all"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[10px] font-black text-amber-400 uppercase">
                    M EGP
                  </span>
                </div>
              </div>

              <button
                onClick={handleMaintenance}
                disabled={maintLoading}
                className="w-full bg-amber-500 text-white py-4 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg shadow-amber-200 hover:bg-amber-600 disabled:opacity-40 transition-all flex items-center justify-center gap-2"
              >
                {maintLoading
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <BarChart3 className="w-4 h-4" />}
                Run DP Optimizer
              </button>

              {/* Result card */}
              {maintResult && (
                <div className="bg-amber-50 border border-amber-100 rounded-2xl p-5 space-y-4 mt-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-black text-amber-500 uppercase tracking-widest">Optimal Plan</span>
                    <span className="text-[9px] font-black bg-amber-500 text-white px-2 py-0.5 rounded-full uppercase">
                      {maintResult.budget_utilization?.toFixed(1)}% Used
                    </span>
                  </div>

                  {/* KPIs */}
                  <div className="flex gap-2">
                    <StatBadge
                      label="Roads Selected"
                      value={maintResult.selected_count}
                      sub={`of ${maintResult.total_candidates}`}
                      color="amber"
                    />
                    <StatBadge
                      label="Total Cost"
                      value={`${maintResult.total_cost_megp?.toFixed(1)}M`}
                      sub={`/ ${maintResult.max_budget_megp}M budget`}
                      color="amber"
                    />
                  </div>
                  <div className="flex gap-2">
                    <StatBadge
                      label="Traffic Benefit"
                      value={maintResult.total_benefit?.toLocaleString()}
                      sub="veh/h restored"
                      color="emerald"
                    />
                    <StatBadge
                      label="Critical Roads"
                      value={criticalRoads}
                      sub="condition < 5"
                      color={criticalRoads > 0 ? 'red' : 'emerald'}
                    />
                  </div>

                  {/* Road list */}
                  <div>
                    <p className="text-[9px] font-black text-slate-400 uppercase mb-2">Selected Roads</p>
                    <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                      {selectedRoads.map((road, i) => (
                        <div
                          key={i}
                          className={`flex items-center justify-between p-2.5 rounded-xl border text-xs ${
                            road.condition < 5
                              ? 'bg-red-50 border-red-100'
                              : 'bg-white border-amber-100'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {road.condition < 5
                              ? <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                              : <CheckCircle2 className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                            }
                            <span className="font-bold text-slate-700">{road.road_id}</span>
                          </div>
                          <div className="text-right">
                            <p className="font-black text-[10px] text-slate-500">
                              cond <span className={road.condition < 5 ? 'text-red-600' : 'text-amber-600'}>{road.condition}/10</span>
                            </p>
                            <p className="font-bold text-[9px] text-slate-400">{road.repair_cost_megp?.toFixed(1)}M EGP</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer stats bar */}
        <div className="shrink-0 px-6 py-4 border-t border-slate-100 bg-slate-50/70 grid grid-cols-4 gap-2">
          {[
            { icon: Building2, val: nodes.length, label: 'Nodes' },
            { icon: Zap,        val: 89,           label: 'Edges' },
            { icon: Bus,        val: 10,           label: 'Bus' },
            { icon: TrainFront, val: 3,            label: 'Metro' },
          ].map(({ icon: Icon, val, label }, i) => (
            <div key={i} className={`flex flex-col items-center ${i > 0 ? 'border-l border-slate-200' : ''}`}>
              <span className="text-sm font-black text-slate-700">{val}</span>
              <span className="text-[8px] font-bold text-slate-400 uppercase">{label}</span>
            </div>
          ))}
        </div>
      </aside>

      {/* ═══════════════ MAIN MAP AREA ═══════════════ */}
      <main className="flex-1 flex flex-col p-4 gap-3 min-w-0">

        {/* Top bar */}
        <header className="shrink-0 flex items-center justify-between px-6 py-3 bg-white/90 backdrop-blur-xl rounded-2xl border border-white shadow-xl z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center shadow-lg">
              <MapIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-black text-slate-800">Cairo Network Map</h2>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[9px] font-black text-emerald-600 uppercase tracking-widest">Live</span>
              </div>
            </div>
          </div>

          {/* Active layer pills */}
          <div className="flex items-center gap-2">
            {routeResult?.found && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 border border-blue-100 rounded-full">
                <div className="w-2 h-2 rounded-full bg-blue-500" />
                <span className="text-[9px] font-black text-blue-600 uppercase">Route Active</span>
              </div>
            )}
            {mstResult && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 border border-orange-100 rounded-full">
                <div className="w-2 h-2 rounded-full bg-orange-500" />
                <span className="text-[9px] font-black text-orange-600 uppercase">MST Active</span>
              </div>
            )}
            {maintResult && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 border border-amber-100 rounded-full">
                <div className="w-2 h-2 rounded-full bg-amber-500" />
                <span className="text-[9px] font-black text-amber-600 uppercase">
                  {maintResult.selected_count} Roads Highlighted
                </span>
              </div>
            )}
            <button className="p-2.5 hover:bg-slate-100 rounded-xl transition-colors">
              <Settings className="w-4 h-4 text-slate-400" />
            </button>
          </div>
        </header>

        {/* Error toast */}
        {error && (
          <div className="shrink-0 bg-red-600 text-white px-6 py-3 rounded-2xl shadow-2xl flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span className="text-sm font-bold flex-1">{error}</span>
            <button onClick={() => setError(null)} className="font-black text-lg leading-none hover:opacity-70">×</button>
          </div>
        )}

        {/* Map */}
        <div className="flex-1 rounded-[2.5rem] overflow-hidden shadow-2xl border-[6px] border-white ring-1 ring-slate-300 min-h-0">
          {appLoading ? (
            <div className="w-full h-full bg-slate-50 flex flex-col items-center justify-center gap-4">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-blue-100 rounded-full" />
                <div className="absolute inset-0 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </div>
              <p className="text-xs font-black text-slate-400 uppercase tracking-widest">Loading Cairo Graph…</p>
            </div>
          ) : (
            <TransportationMap
              nodes={nodes}
              routeResult={routeResult}
              mstResult={mstResult}
              maintResult={maintResult}
            />
          )}
        </div>
      </main>
    </div>
  );
}
