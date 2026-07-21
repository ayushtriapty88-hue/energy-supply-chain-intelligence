import React, { useState } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  Line,
} from 'react-simple-maps';

const GEO_URL =
  'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

const RISK_COLORS = {
  LOW: '#22c55e',
  MEDIUM: '#f59e0b',
  HIGH: '#ef4444',
  CRITICAL: '#7c3aed',
  UNKNOWN: '#6b7280',
};

// Real coordinates: [longitude, latitude]
const INDIA = [78.0, 22.0];

// Static reference facts per corridor (merged with live backend data on click)
const CORRIDORS = {
  strait_of_hormuz: {
    name: 'Strait of Hormuz', coords: [56.3, 26.6],
    facts: {
      'Daily oil flow': '~21 million barrels/day (20% of global supply)',
      'Width at narrowest': '33 km',
      'India dependency': '~45% of crude imports transit here',
      'Chief risk': 'Iranian naval blockade / mining',
    },
  },
  red_sea: {
    name: 'Red Sea', coords: [38.0, 20.0],
    facts: {
      'Route': 'Suez ↔ Bab-el-Mandeb corridor',
      'Chief risk': 'Houthi drone & missile attacks on tankers',
      'Detour if closed': 'Cape of Good Hope (+10–14 days)',
    },
  },
  suez_canal: {
    name: 'Suez Canal', coords: [32.3, 30.0],
    facts: {
      'Traffic': '~12% of global trade',
      'Chief risk': 'Blockage / regional escalation',
      'Detour if closed': 'Cape of Good Hope',
    },
  },
  cape_of_good_hope: {
    name: 'Cape of Good Hope', coords: [18.5, -34.4],
    facts: {
      'Role': 'Safe alternative route around Africa',
      'Added transit': '+10–14 days vs Suez',
      'Chief risk': 'None — open water, longer & costlier',
    },
  },
};

// Static supplier facts
const SUPPLIERS = [
  { name: 'Saudi Arabia', key: 'saudi', coords: [45.0, 24.0], color: '#22c55e',
    facts: { 'Available': '500 kbd', 'Grade': 'Arab Light', 'Route': 'Persian Gulf',
             'Sanction risk': 'LOW', 'Delivery': '~8 days' } },
  { name: 'Iraq', key: 'iraq', coords: [43.7, 33.2], color: '#22c55e',
    facts: { 'Available': '400 kbd', 'Grade': 'Basra Medium', 'Route': 'Persian Gulf',
             'Sanction risk': 'LOW', 'Delivery': '~7 days' } },
  { name: 'UAE', key: 'uae', coords: [54.0, 24.0], color: '#22c55e',
    facts: { 'Available': '200 kbd', 'Grade': 'Murban', 'Route': 'Persian Gulf',
             'Sanction risk': 'LOW', 'Delivery': '~6 days' } },
  { name: 'Nigeria', key: 'nigeria', coords: [8.7, 9.1], color: '#60a5fa',
    facts: { 'Available': '200 kbd', 'Grade': 'Bonny Light', 'Route': 'Cape of Good Hope',
             'Sanction risk': 'NONE', 'Delivery': '~18 days' } },
  { name: 'Angola', key: 'angola', coords: [17.9, -11.2], color: '#60a5fa',
    facts: { 'Available': '150 kbd', 'Grade': 'Cabinda', 'Route': 'Cape of Good Hope',
             'Sanction risk': 'NONE', 'Delivery': '~16 days' } },
  { name: 'Russia', key: 'russia', coords: [45.0, 55.0], color: '#f59e0b',
    facts: { 'Share of imports': '38%', 'Grade': 'Urals', 'Route': 'Direct',
             'Sanction risk': 'MEDIUM — price cap $60/bbl', 'Delivery': '~12 days' } },
];

const OCEANS = [
  { name: 'ARABIAN SEA',    coords: [63, 14],  size: 11 },
  { name: 'BAY OF BENGAL',  coords: [88, 13],  size: 11 },
  { name: 'INDIAN OCEAN',   coords: [72, -12], size: 13 },
  { name: 'RED SEA',        coords: [40.5, 15], size: 8  },
  { name: 'PERSIAN\nGULF',  coords: [51, 29],  size: 7  },
  { name: 'ATLANTIC\nOCEAN', coords: [-2, -18], size: 11 },
];

function laneColor(corridors, key, fallback) {
  return RISK_COLORS[corridors?.[key]?.risk_level] || fallback;
}

export default function WorldMap({ corridors = {} }) {
  const [hover, setHover] = useState(null);
  const [selected, setSelected] = useState(null); // { title, color, rows: [[k,v],...], x, y }

  // Build the detail payload for a corridor (live + static)
  const openCorridor = (key, evt) => {
    const live = corridors?.[key] || {};
    const c = CORRIDORS[key];
    const rows = [];
    if (live.risk_score !== undefined) rows.push(['Risk score', `${live.risk_score}/100 · ${live.risk_level || '—'}`]);
    if (live.vessels_moving !== undefined) rows.push(['Vessels moving', live.vessels_moving]);
    if (live.vessels_stopped !== undefined) rows.push(['Stopped / diverted', live.vessels_stopped]);
    if (live.primary_threat) rows.push(['AI threat', live.primary_threat]);
    if (live.recommendation) rows.push(['Recommendation', live.recommendation]);
    Object.entries(c.facts).forEach(([k, v]) => rows.push([k, v]));
    setSelected({
      title: c.name,
      color: RISK_COLORS[live.risk_level] || '#6b7280',
      badge: live.risk_level || null,
      rows,
      x: evt.clientX, y: evt.clientY,
    });
  };

  const openSupplier = (s, evt) => {
    const rows = Object.entries(s.facts);
    setSelected({
      title: s.name, color: s.color, badge: 'SUPPLIER',
      rows, x: evt.clientX, y: evt.clientY,
    });
  };

  const openIndia = (evt) => {
    setSelected({
      title: 'India — Demand Centre', color: '#60a5fa', badge: 'CONSUMER',
      rows: [
        ['Daily consumption', '5,200 kbd'],
        ['Import dependency', '88% of crude'],
        ['Via Hormuz', '~45% of imports'],
        ['Strategic reserve', '~7.5 days of cover'],
        ['Top current supplier', 'Russia (38%)'],
      ],
      x: evt.clientX, y: evt.clientY,
    });
  };

  return (
    <div style={{ position: 'relative', width: '100%', background: '#0a1628', borderRadius: '8px', overflow: 'hidden' }}
         onClick={(e) => { if (e.target === e.currentTarget) setSelected(null); }}>
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ scale: 340, center: [55, 12] }}
        style={{ width: '100%', height: '520px' }}
      >
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                fill="#16233b"
                stroke="#24344f"
                strokeWidth={0.4}
                style={{
                  default: { outline: 'none' },
                  hover:   { fill: '#1d2f4d', outline: 'none' },
                  pressed: { outline: 'none' },
                }}
              />
            ))
          }
        </Geographies>

        {/* Ocean / sea labels */}
        {OCEANS.map((o) => (
          <Marker key={o.name} coordinates={o.coords}>
            {o.name.split('\n').map((line, i) => (
              <text
                key={i}
                textAnchor="middle"
                y={i * (o.size + 2)}
                style={{
                  fill: '#3b5578', fontSize: o.size, fontWeight: 600,
                  letterSpacing: '0.15em', pointerEvents: 'none', textTransform: 'uppercase',
                }}
              >
                {line}
              </text>
            ))}
          </Marker>
        ))}

        {/* Shipping lanes */}
        <Line from={CORRIDORS.strait_of_hormuz.coords} to={INDIA}
          stroke={laneColor(corridors, 'strait_of_hormuz', '#6b7280')}
          strokeWidth={2} strokeDasharray="6 4" strokeLinecap="round" />
        <Line from={CORRIDORS.red_sea.coords} to={CORRIDORS.strait_of_hormuz.coords}
          stroke={laneColor(corridors, 'red_sea', '#6b7280')}
          strokeWidth={2} strokeDasharray="6 4" strokeLinecap="round" />
        <Line from={CORRIDORS.cape_of_good_hope.coords} to={INDIA}
          stroke={laneColor(corridors, 'cape_of_good_hope', '#22c55e')}
          strokeWidth={1.5} strokeDasharray="4 4" strokeLinecap="round" />
        {SUPPLIERS.filter(s => s.color === '#60a5fa').map(s => (
          <Line key={`lane-${s.name}`} from={s.coords} to={CORRIDORS.cape_of_good_hope.coords}
            stroke="#60a5fa" strokeWidth={1} strokeDasharray="3 4" strokeLinecap="round" opacity={0.5} />
        ))}

        {/* Corridor markers */}
        {Object.entries(CORRIDORS).map(([key, c]) => {
          const level = corridors?.[key]?.risk_level || 'UNKNOWN';
          const score = corridors?.[key]?.risk_score;
          const color = RISK_COLORS[level] || '#6b7280';
          const isSel = selected?.title === c.name;
          return (
            <Marker key={key} coordinates={c.coords}
              onMouseEnter={() => setHover({ name: c.name, sub: `${score ?? '—'}/100 · ${level} — click for detail` })}
              onMouseLeave={() => setHover(null)}
              onClick={(e) => openCorridor(key, e)}
              style={{ default: { cursor: 'pointer' }, hover: { cursor: 'pointer' } }}
            >
              <circle r={isSel ? 13 : 9} fill={color} opacity={0.25} />
              <circle r={5} fill={color} stroke={isSel ? '#fff' : '#0a1628'} strokeWidth={isSel ? 2 : 1} style={{ cursor: 'pointer' }} />
              <text textAnchor="middle" y={-13}
                style={{ fill: '#f1f5f9', fontSize: 9, fontWeight: 700, pointerEvents: 'none' }}>
                {c.name.replace('Strait of ', '')}
              </text>
            </Marker>
          );
        })}

        {/* Supplier markers */}
        {SUPPLIERS.map((s) => {
          const isSel = selected?.title === s.name;
          return (
            <Marker key={s.name} coordinates={s.coords}
              onMouseEnter={() => setHover({ name: s.name, sub: 'Supplier — click for detail' })}
              onMouseLeave={() => setHover(null)}
              onClick={(e) => openSupplier(s, e)}
              style={{ default: { cursor: 'pointer' }, hover: { cursor: 'pointer' } }}
            >
              <circle r={isSel ? 7 : 4} fill={s.color} stroke={isSel ? '#fff' : '#0a1628'} strokeWidth={isSel ? 2 : 1} style={{ cursor: 'pointer' }} />
              <text textAnchor="middle" y={-8}
                style={{ fill: s.color, fontSize: 8, fontWeight: 600, pointerEvents: 'none' }}>
                {s.name}
              </text>
            </Marker>
          );
        })}

        {/* India */}
        <Marker coordinates={INDIA}
          onMouseEnter={() => setHover({ name: 'India', sub: 'Demand centre — click for detail' })}
          onMouseLeave={() => setHover(null)}
          onClick={(e) => openIndia(e)}
          style={{ default: { cursor: 'pointer' }, hover: { cursor: 'pointer' } }}
        >
          <circle r={11} fill="#60a5fa" opacity={0.25} />
          <circle r={6} fill="#60a5fa" stroke="#0a1628" strokeWidth={1.5} style={{ cursor: 'pointer' }} />
          <text textAnchor="middle" y={-14}
            style={{ fill: '#60a5fa', fontSize: 11, fontWeight: 700, pointerEvents: 'none' }}>
            India
          </text>
        </Marker>
      </ComposableMap>

      {/* Title */}
      <div style={{ position: 'absolute', top: 12, left: 16, fontSize: 13, fontWeight: 700, color: '#94a3b8', pointerEvents: 'none' }}>
        Indian Ocean Energy Corridor Intelligence Map
        <div style={{ fontSize: 10, color: '#64748b', fontWeight: 400, marginTop: 2 }}>
          Real geography · live risk colours · click any point for detail
        </div>
      </div>

      {/* Hover hint (only when nothing is selected) */}
      {hover && !selected && (
        <div style={{ position: 'absolute', bottom: 12, left: 16, background: '#1e293b',
          border: '1px solid #334155', borderRadius: 8, padding: '8px 12px', pointerEvents: 'none' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#f1f5f9' }}>{hover.name}</div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>{hover.sub}</div>
        </div>
      )}

      {/* Legend */}
      <div style={{ position: 'absolute', bottom: 12, right: 16, background: 'rgba(30,41,59,0.95)',
        borderRadius: 8, padding: '10px 12px', fontSize: 10, color: '#f1f5f9' }}>
        {[
          ['#ef4444', 'HIGH risk corridor'],
          ['#f59e0b', 'MEDIUM risk corridor'],
          ['#22c55e', 'LOW / safe route'],
          ['#60a5fa', 'Alt. supplier'],
        ].map(([c, label]) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0' }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: c, display: 'inline-block' }} />
            {label}
          </div>
        ))}
      </div>

      {/* Floating detail popup near the clicked dot */}
      {selected && (
        <FloatingCard selected={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function FloatingCard({ selected, onClose }) {
  const CARD_W = 300;
  const MARGIN = 16;
  const vw = typeof window !== 'undefined' ? window.innerWidth  : 1200;
  const vh = typeof window !== 'undefined' ? window.innerHeight : 800;

  // Card is capped at 70vh tall; reserve that much space when clamping.
  const cardMaxH = Math.min(vh * 0.7, vh - 2 * MARGIN);

  // Horizontal: prefer right of the dot, flip left if it would overflow.
  let left = selected.x + MARGIN;
  if (left + CARD_W > vw - MARGIN) left = selected.x - CARD_W - MARGIN;
  if (left < MARGIN) left = MARGIN;

  // Vertical: start near the dot, but never let the card run past the
  // bottom (or top) of the screen — always fully visible.
  let top = selected.y - 40;
  if (top + cardMaxH > vh - MARGIN) top = vh - cardMaxH - MARGIN;
  if (top < MARGIN) top = MARGIN;

  return (
    <div style={{
      position: 'fixed', left, top, width: CARD_W, zIndex: 500,
      maxHeight: `${cardMaxH}px`, display: 'flex', flexDirection: 'column',
      background: '#1e293b', border: `1px solid ${selected.color}`,
      borderRadius: 12, padding: '14px 16px',
      boxShadow: '0 12px 40px rgba(0,0,0,0.55)',
      color: '#f1f5f9', fontFamily: "'Inter', sans-serif",
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: selected.color, display: 'inline-block' }} />
          <span style={{ fontSize: 14, fontWeight: 700 }}>{selected.title}</span>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 14 }}>✕</button>
      </div>
      {selected.badge && (
        <span style={{
          display: 'inline-block', marginBottom: 10, fontSize: 10, fontWeight: 700,
          letterSpacing: '0.06em', color: '#fff', background: selected.color,
          padding: '2px 10px', borderRadius: 999,
        }}>{selected.badge}</span>
      )}
      {/* scrollable content below */}
      <div style={{ overflowY: 'auto', flex: 1, marginRight: -6, paddingRight: 6 }}>
        {selected.rows.map(([k, v], i) => (
          <div key={i} style={{
            padding: '6px 0',
            borderBottom: i < selected.rows.length - 1 ? '1px solid #334155' : 'none',
          }}>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{k}</div>
            <div style={{ fontSize: 13, color: '#f1f5f9', marginTop: 1, lineHeight: 1.4 }}>{String(v)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}