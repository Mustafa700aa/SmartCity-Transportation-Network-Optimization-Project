import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Fix default icon
L.Marker.prototype.options.icon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});

// Custom small dot icon for all network nodes
const makeNodeIcon = (color, size = 8) => L.divIcon({
  className: '',
  html: `<div style="
    background:${color};
    width:${size}px;
    height:${size}px;
    border-radius:50%;
    border:2px solid rgba(255,255,255,0.9);
    box-shadow:0 1px 4px rgba(0,0,0,0.25);
  "></div>`,
  iconSize: [size, size],
  iconAnchor: [size / 2, size / 2],
});

const icons = {
  default:     makeNodeIcon('#64748b', 8),
  routeStart:  makeNodeIcon('#10b981', 14),
  routeEnd:    makeNodeIcon('#ef4444', 14),
  routeWay:    makeNodeIcon('#3b82f6', 10),
  mstNode:     makeNodeIcon('#22c55e', 11),   // FIX-3: bright green
  maintNode:   makeNodeIcon('#f59e0b', 10),
};

const CAIRO_CENTER = [30.0444, 31.2357];

/**
 * Main Leaflet map component.
 *
 * Props:
 *  nodes          – array of { id, name, type, source, x, y, population } from /api/graph
 *  routeResult    – RouteResult from /api/route or /api/astar  (or null)
 *  mstResult      – MSTResult from /api/mst                    (or null)
 *  maintResult    – MaintenanceResult from /api/maintenance     (or null)
 *
 * Coordinate convention:  Leaflet = [lat, lng] = [node.y, node.x]
 */
export default function TransportationMap({
  nodes = [],
  routeResult = null,
  mstResult = null,
  maintResult = null,
}) {
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));
  const pos = (id) => { const n = nodeMap[id]; return n ? [n.y, n.x] : null; };

  // Route path as [lat,lng] array
  const routePositions = (routeResult?.path || []).map(pos).filter(Boolean);

  // Maintenance – only selected roads
  const selectedRoads = (maintResult?.candidates || []).filter(c => c.selected);

  // Which nodes appear in MST edges (for distinct icons)
  const mstNodeIds = new Set(
    (mstResult?.mst_edges || []).flatMap(e => [e.from_id, e.to_id])
  );

  // Active layer flags
  const hasRoute = routePositions.length > 1;
  const hasMST   = (mstResult?.mst_edges || []).length > 0;
  const hasMaint = selectedRoads.length > 0;

  // Legend entries depend on what is visible
  const legendItems = [
    { color: '#64748b', label: 'Network Node',           always: true,  dot: true  },
    { color: '#3b82f6', label: 'Optimal Route',           show: hasRoute, dot: false },
    { color: '#10b981', label: 'Route Start',             show: hasRoute, dot: true  },
    { color: '#ef4444', label: 'Route End',               show: hasRoute, dot: true  },
    { color: '#22c55e', label: 'MST Proposed Road',       show: hasMST,  dot: false },  // FIX-3
    { color: '#f59e0b', label: 'Road for Repair (Good)',  show: hasMaint, dot: false },
    { color: '#dc2626', label: 'Road for Repair (Critical)', show: hasMaint, dot: false },
  ];

  return (
    <div className="w-full h-full relative">
      <MapContainer
        center={CAIRO_CENTER}
        zoom={11}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <ZoomControl position="bottomright" />

        {/* CartoDB Light base-map */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />

        {/* ── All network nodes ── */}
        {nodes.map(n => {
          let icon = icons.default;
          if (hasRoute && routeResult.path[0] === n.id)                                         icon = icons.routeStart;
          else if (hasRoute && routeResult.path[routeResult.path.length - 1] === n.id)          icon = icons.routeEnd;
          else if (hasRoute && routeResult.path.includes(n.id))                                  icon = icons.routeWay;
          else if (mstNodeIds.has(n.id))                                                         icon = icons.mstNode;
          return (
            <Marker key={n.id} position={[n.y, n.x]} icon={icon}>
              <Popup>
                <div className="min-w-[140px]">
                  <p className="font-bold text-slate-800">{n.name}</p>
                  <p className="text-[10px] text-slate-400 font-bold uppercase">{n.type} · {n.id}</p>
                  {n.population && (
                    <p className="text-xs mt-1 text-slate-600">
                      Population: {n.population.toLocaleString()}
                    </p>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* ── Optimal Route polyline ── */}
        {hasRoute && (
          <>
            {/* Glow layer */}
            <Polyline
              positions={routePositions}
              pathOptions={{ color: '#3b82f6', weight: 10, opacity: 0.15 }}
            />
            {/* Main line */}
            <Polyline
              positions={routePositions}
              pathOptions={{ color: '#3b82f6', weight: 4, opacity: 0.9 }}
            />
            {/* Animated dash overlay */}
            <Polyline
              positions={routePositions}
              pathOptions={{ color: '#ffffff', weight: 2, opacity: 0.6, dashArray: '8 14' }}
            />
          </>
        )}

        {/* ── MST proposed roads — FIX-3: BRIGHT GREEN ── */}
        {(mstResult?.mst_edges || []).map((edge, idx) => {
          const a = pos(edge.from_id), b = pos(edge.to_id);
          if (!a || !b) return null;
          return (
            <React.Fragment key={`mst-${idx}`}>
              {/* Glow halo */}
              <Polyline
                positions={[a, b]}
                pathOptions={{ color: '#86efac', weight: 12, opacity: 0.35 }}
              />
              {/* Main green road */}
              <Polyline
                positions={[a, b]}
                pathOptions={{ color: '#22c55e', weight: 5, opacity: 0.9, dashArray: '8 6' }}
              >
                <Popup>
                  <p className="font-bold text-green-700">Proposed Road</p>
                  <p className="text-xs text-slate-500">{edge.from_id} → {edge.to_id}</p>
                  <p className="text-xs text-green-600 font-semibold">Cost: {edge.construction_cost} M EGP</p>
                </Popup>
              </Polyline>
            </React.Fragment>
          );
        })}

        {/* ── Maintenance: selected roads ── */}
        {selectedRoads.map((road, idx) => {
          const [fromId, toId] = road.road_id.split('-');
          const a = pos(fromId), b = pos(toId);
          if (!a || !b) return null;

          // Color by condition severity: condition < 5 = critical (red), else amber
          const isCritical = road.condition < 5;
          const color  = isCritical ? '#dc2626' : '#f59e0b';
          const glow   = isCritical ? '#fca5a5' : '#fde68a';

          return (
            <React.Fragment key={`maint-${idx}`}>
              {/* Glow halo */}
              <Polyline
                positions={[a, b]}
                pathOptions={{ color: glow, weight: 14, opacity: 0.3 }}
              />
              {/* Main maintenance highlight */}
              <Polyline
                positions={[a, b]}
                pathOptions={{ color, weight: 6, opacity: 1 }}
              >
                <Popup>
                  <div className="min-w-[180px]">
                    <p className="font-bold text-slate-800">Road {road.road_id}</p>
                    <p className="text-xs text-slate-500 mb-2">{road.from_name} → {road.to_name}</p>
                    <div className="grid grid-cols-2 gap-1 text-[10px]">
                      <span className="font-bold text-slate-400">CONDITION</span>
                      <span className={`font-black ${isCritical ? 'text-red-600' : 'text-amber-600'}`}>
                        {road.condition}/10 {isCritical ? '⚠️' : ''}
                      </span>
                      <span className="font-bold text-slate-400">COST</span>
                      <span className="font-black text-slate-700">{road.repair_cost_megp.toFixed(2)}M EGP</span>
                      <span className="font-bold text-slate-400">BENEFIT</span>
                      <span className="font-black text-slate-700">{road.traffic_benefit.toLocaleString()} veh/h</span>
                    </div>
                  </div>
                </Popup>
              </Polyline>
              {/* Dash stripe for texture */}
              <Polyline
                positions={[a, b]}
                pathOptions={{ color: '#ffffff', weight: 2, opacity: 0.5, dashArray: '4 10' }}
              />
            </React.Fragment>
          );
        })}
      </MapContainer>

      {/* ── Legend overlay ── */}
      <div className="absolute bottom-6 left-6 bg-white/95 backdrop-blur-md p-4 rounded-2xl shadow-xl border border-slate-200 z-[1000] space-y-2 min-w-[170px]">
        <h4 className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3">Map Legend</h4>
        {legendItems.filter(i => i.always || i.show).map((item, i) => (
          <div key={i} className="flex items-center gap-2.5">
            {item.dot ? (
              <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
            ) : (
              <div className="w-5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
            )}
            <span className="text-[10px] font-semibold text-slate-600">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
