import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts';
import './App.css';
import LandingScreen from './LandingScreen';
import WorldMap from './WorldMap';
import GuidedTour, { TOUR_STEPS } from './GuidedTour';

const API = 'http://localhost:8000/api';

const RISK_COLORS = {
  LOW:      '#22c55e',
  MEDIUM:   '#f59e0b',
  HIGH:     '#ef4444',
  CRITICAL: '#7c3aed',
  UNKNOWN:  '#6b7280',
};

const SCENARIOS = [
  { key: 'hormuz_partial',     label: 'Hormuz Partial' },
  { key: 'hormuz_closure',     label: 'Hormuz Full Closure' },
  { key: 'red_sea_closure',    label: 'Red Sea Shutdown' },
  { key: 'opec_emergency_cut', label: 'OPEC+ Emergency Cut' },
  { key: 'russia_sanctions',   label: 'Russia Full Embargo' },
];

const fmt = (v, suffix = '') => (v === undefined || v === null ? '—' : `${v}${suffix}`);

// Turns ANY value into safe text so React never crashes on a raw object.
const safeText = (v) => {
  if (v === undefined || v === null) return '';
  if (typeof v === 'string' || typeof v === 'number') return v;
  if (typeof v === 'object') {
    return v.action || v.text || v.title || v.recommendation ||
           v.item || v.name || v.description ||
           [v.country, v.action].filter(Boolean).join(' — ') ||
           JSON.stringify(v);
  }
  return String(v);
};

function RiskBadge({ level }) {
  return (
    <span style={{
      background:    RISK_COLORS[level] || '#6b7280',
      color:         '#fff',
      padding:       '2px 10px',
      borderRadius:  '999px',
      fontSize:      '12px',
      fontWeight:    700,
      letterSpacing: '0.05em',
    }}>
      {level}
    </span>
  );
}

function Card({ title, children, accent }) {
  return (
    <div style={{
      background:   '#1e293b',
      border:       `1px solid ${accent || '#334155'}`,
      borderRadius: '12px',
      padding:      '20px',
      marginBottom: '16px',
    }}>
      {title && (
        <div style={{
          fontSize:      '11px',
          fontWeight:    700,
          letterSpacing: '0.1em',
          color:         '#94a3b8',
          marginBottom:  '12px',
          textTransform: 'uppercase',
        }}>
          {title}
        </div>
      )}
      {children}
    </div>
  );
}

function ScoreGauge({ score, level }) {
  const color = RISK_COLORS[level] || '#6b7280';
  return (
    <div style={{ textAlign: 'center', padding: '10px 0' }}>
      <div style={{ fontSize: '64px', fontWeight: 900, color, lineHeight: 1 }}>
        {score}
      </div>
      <div style={{ fontSize: '14px', color: '#94a3b8', marginTop: '4px' }}>/ 100</div>
      <div style={{ marginTop: '8px' }}>
        <RiskBadge level={level} />
      </div>
    </div>
  );
}

function SVGMap({ corridors }) {
  return (
    <svg viewBox="0 0 900 520" style={{ width: '100%', height: '520px', background: '#0a1628', borderRadius: '8px' }}>
      {[100,200,300,400,500,600,700,800].map(x => (
        <line key={`vx${x}`} x1={x} y1="0" x2={x} y2="520" stroke="#1e3a5f" strokeWidth="0.5" opacity="0.4"/>
      ))}
      {[100,200,300,400].map(y => (
        <line key={`hy${y}`} x1="0" y1={y} x2="900" y2={y} stroke="#1e3a5f" strokeWidth="0.5" opacity="0.4"/>
      ))}

      <ellipse cx="200" cy="280" rx="90" ry="140" fill="#1a2f1a" opacity="0.8"/>
      <ellipse cx="460" cy="200" rx="70" ry="60" fill="#2a2a1a" opacity="0.8"/>
      <ellipse cx="520" cy="160" rx="60" ry="40" fill="#2a2a1a" opacity="0.8"/>
      <ellipse cx="680" cy="280" rx="55" ry="80" fill="#1a2f1a" opacity="0.8"/>
      <rect x="400" y="0" width="300" height="60" fill="#1a1a2a" opacity="0.6"/>
      <ellipse cx="220" cy="80" rx="80" ry="50" fill="#1a1a2a" opacity="0.6"/>

      <polyline
        points="545,195 570,210 600,230 630,245 660,255 680,260"
        fill="none"
        stroke={RISK_COLORS[corridors.strait_of_hormuz?.risk_level] || '#6b7280'}
        strokeWidth="3" strokeDasharray="8 4" opacity="0.9"
      />
      <polyline
        points="310,160 340,195 370,220 400,235 430,245 460,252 500,255 550,258 620,260 660,262 680,265"
        fill="none"
        stroke={RISK_COLORS[corridors.red_sea?.risk_level] || '#6b7280'}
        strokeWidth="3" strokeDasharray="8 4" opacity="0.9"
      />
      <polyline
        points="190,380 200,420 215,460 230,490 260,500 310,490 360,470 400,440 440,410 480,390 530,375 580,368 630,365 665,360 680,358"
        fill="none"
        stroke={RISK_COLORS[corridors.cape_of_good_hope?.risk_level] || '#22c55e'}
        strokeWidth="2" strokeDasharray="4 4" opacity="0.7"
      />
      <polyline points="155,310 165,360 175,400 185,430 195,460"
        fill="none" stroke="#60a5fa" strokeWidth="2" strokeDasharray="4 4" opacity="0.6"/>
      <polyline points="580,40 590,80 600,120 610,160 630,200 650,240 665,280 675,320 678,350"
        fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="4 4" opacity="0.5"/>

      <circle cx="545" cy="195" r="14" fill={RISK_COLORS[corridors.strait_of_hormuz?.risk_level] || '#6b7280'} opacity="0.3"/>
      <circle cx="545" cy="195" r="8"  fill={RISK_COLORS[corridors.strait_of_hormuz?.risk_level] || '#6b7280'} opacity="0.9"/>
      <text x="555" y="183" fill="#f1f5f9" fontSize="10" fontWeight="bold">Hormuz</text>
      <text x="555" y="194" fill="#94a3b8" fontSize="9">
        {fmt(corridors.strait_of_hormuz?.risk_score)}/100 — {fmt(corridors.strait_of_hormuz?.risk_level)}
      </text>

      <circle cx="355" cy="220" r="14" fill={RISK_COLORS[corridors.red_sea?.risk_level] || '#6b7280'} opacity="0.3"/>
      <circle cx="355" cy="220" r="8"  fill={RISK_COLORS[corridors.red_sea?.risk_level] || '#6b7280'} opacity="0.9"/>
      <text x="365" y="215" fill="#f1f5f9" fontSize="10" fontWeight="bold">Red Sea</text>
      <text x="365" y="226" fill="#94a3b8" fontSize="9">
        {fmt(corridors.red_sea?.risk_score)}/100 — {fmt(corridors.red_sea?.risk_level)}
      </text>

      <circle cx="312" cy="155" r="10" fill={RISK_COLORS[corridors.suez_canal?.risk_level] || '#22c55e'} opacity="0.9"/>
      <text x="322" y="150" fill="#f1f5f9" fontSize="10" fontWeight="bold">Suez</text>
      <text x="322" y="161" fill="#94a3b8" fontSize="9">{fmt(corridors.suez_canal?.risk_score)}/100</text>

      <circle cx="215" cy="480" r="10" fill={RISK_COLORS[corridors.cape_of_good_hope?.risk_level] || '#22c55e'} opacity="0.9"/>
      <text x="228" y="475" fill="#f1f5f9" fontSize="10" fontWeight="bold">Cape of Good Hope</text>
      <text x="228" y="486" fill="#94a3b8" fontSize="9">{fmt(corridors.cape_of_good_hope?.risk_score)}/100 — SAFE ROUTE</text>

      <circle cx="678" cy="280" r="16" fill="#60a5fa" opacity="0.25"/>
      <circle cx="678" cy="280" r="8"  fill="#60a5fa" opacity="0.9"/>
      <text x="692" y="272" fill="#60a5fa" fontSize="11" fontWeight="bold">🇮🇳 India</text>
      <text x="692" y="284" fill="#94a3b8" fontSize="9">5,200 kbd consumed</text>
      <text x="692" y="295" fill="#94a3b8" fontSize="9">SPR: ~7.5 days cover</text>

      <circle cx="155" cy="310" r="7" fill="#60a5fa" opacity="0.9"/>
      <text x="165" y="307" fill="#60a5fa" fontSize="10" fontWeight="bold">Nigeria</text>
      <text x="165" y="318" fill="#94a3b8" fontSize="9">200 kbd | Zero sanctions</text>

      <circle cx="460" cy="210" r="7" fill="#22c55e" opacity="0.9"/>
      <text x="470" y="207" fill="#22c55e" fontSize="10" fontWeight="bold">Saudi Arabia</text>
      <text x="470" y="218" fill="#94a3b8" fontSize="9">500 kbd available</text>

      <circle cx="490" cy="175" r="7" fill="#22c55e" opacity="0.9"/>
      <text x="500" y="172" fill="#22c55e" fontSize="10" fontWeight="bold">Iraq</text>
      <text x="500" y="183" fill="#94a3b8" fontSize="9">400 kbd available</text>

      <circle cx="535" cy="212" r="6" fill="#22c55e" opacity="0.9"/>
      <text x="543" y="216" fill="#22c55e" fontSize="10" fontWeight="bold">UAE</text>

      <circle cx="580" cy="45" r="7" fill="#f59e0b" opacity="0.9"/>
      <text x="590" y="42" fill="#f59e0b" fontSize="10" fontWeight="bold">Russia ⚠</text>
      <text x="590" y="53" fill="#94a3b8" fontSize="9">38% of India imports | Sanction risk</text>

      <circle cx="190" cy="390" r="7" fill="#60a5fa" opacity="0.9"/>
      <text x="200" y="387" fill="#60a5fa" fontSize="10" fontWeight="bold">Angola</text>
      <text x="200" y="398" fill="#94a3b8" fontSize="9">150 kbd available</text>

      <text x="20" y="25" fill="#94a3b8" fontSize="13" fontWeight="bold">
        Indian Ocean Energy Corridor Intelligence Map
      </text>
      <text x="20" y="40" fill="#64748b" fontSize="10">
        Live risk levels — colors update from real-time analysis
      </text>

      <rect x="20" y="455" width="175" height="58" rx="6" fill="#1e293b" opacity="0.95"/>
      <circle cx="35" cy="469" r="5" fill="#ef4444"/>
      <text x="44" y="473" fill="#f1f5f9" fontSize="9">HIGH risk corridor</text>
      <circle cx="35" cy="484" r="5" fill="#f59e0b"/>
      <text x="44" y="488" fill="#f1f5f9" fontSize="9">MEDIUM risk corridor</text>
      <circle cx="35" cy="499" r="5" fill="#22c55e"/>
      <text x="44" y="503" fill="#f1f5f9" fontSize="9">LOW / safe route</text>
      <circle cx="120" cy="469" r="5" fill="#60a5fa"/>
      <text x="129" y="473" fill="#f1f5f9" fontSize="9">Alt. supply</text>
    </svg>
  );
}

export default function App() {
  const [twin,        setTwin]        = useState(null);
  const [scenario,    setScenario]    = useState(null);
  const [procurement, setProcurement] = useState(null);
  const [spr,         setSpr]         = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [activeTab,   setActiveTab]   = useState('overview');
  const [triggering,  setTriggering]  = useState(false);
  const [runningKey,  setRunningKey]  = useState(null);
  const [lastRefresh, setLastRefresh] = useState('');

  // Landing + guided tour
  const [showLanding, setShowLanding] = useState(true);
  const [tourStep,    setTourStep]    = useState(-1);   // -1 = tour off

  const fetchAll = async () => {
    try {
      const [t, s, p, r] = await Promise.all([
        axios.get(`${API}/twin`),
        axios.get(`${API}/scenario`),
        axios.get(`${API}/procurement`),
        axios.get(`${API}/spr`),
      ]);
      setTwin(t.data);
      setScenario(s.data);
      setProcurement(p.data);
      setSpr(r.data);
      setLastRefresh(new Date().toLocaleTimeString());
    } catch (e) {
      console.error('API error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => {
      if (!triggering) fetchAll();
    }, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggering]);

  const triggerScenario = async (key) => {
    setTriggering(true);
    setRunningKey(key);
    try {
      await axios.post(`${API}/run-scenario/${key}`, null, { timeout: 600000 });
      await fetchAll();
    } catch (e) {
      console.error('Scenario failed:', e);
      alert('Scenario run failed — check the backend terminal.');
    } finally {
      setTriggering(false);
      setRunningKey(null);
    }
  };

  // Guided tour handlers
  const startTour = () => {
    setShowLanding(false);
    setActiveTab(TOUR_STEPS[0].tab);
    setTourStep(0);
  };
  const nextTourStep = () => {
    const next = tourStep + 1;
    setActiveTab(TOUR_STEPS[next].tab);
    setTourStep(next);
  };
  const backTourStep = () => {
    const prev = tourStep - 1;
    setActiveTab(TOUR_STEPS[prev].tab);
    setTourStep(prev);
  };
  const finishTour = () => setTourStep(-1);

  if (loading) return (
    <div style={{
      background: '#0f172a', color: '#fff',
      height: '100vh', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      fontSize: '20px',
    }}>
      Loading Energy Intelligence...
    </div>
  );

  if (showLanding) {
    return (
      <LandingScreen
        onEnter={() => setShowLanding(false)}
        onTour={startTour}
      />
    );
  }

  const risk        = twin?.master_risk       || {};
  const corridors   = twin?.corridors         || {};
  const commodities = twin?.commodities       || {};
  const news        = twin?.news              || {};
  const actions     = twin?.immediate_actions || [];

  const corridorChartData = Object.entries(corridors).map(([name, data]) => ({
    name:  name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    score: data.risk_score || 0,
    fill:  RISK_COLORS[data.risk_level] || '#6b7280',
  }));

  const sprTimeline = (spr?.timeline || []).slice(0, 10).map(t => ({
    day:      `D${t.day}`,
    stock_kb: t.spr_remaining_kb,
    draw_kbd: t.spr_draw_kbd,
  }));

  const sch      = spr?.schedule || {};
  const procPlan = procurement?.procurement_plan?.slice(0, 5) || [];
  const exec     = procurement?.executive_summary || {};
  const tabs     = ['overview', 'news', 'corridors', 'scenario', 'map', 'procurement', 'spr'];

  return (
    <div style={{
      background: '#0f172a',
      color:      '#f1f5f9',
      minHeight:  '100vh',
      fontFamily: "'Inter', -apple-system, sans-serif",
    }}>

      {/* Guided tour overlay */}
      {tourStep >= 0 && (
        <GuidedTour
          steps={TOUR_STEPS}
          stepIndex={tourStep}
          onNext={nextTourStep}
          onBack={backTourStep}
          onFinish={finishTour}
        />
      )}

      {/* Blocking overlay while a scenario runs */}
      {triggering && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          background: 'rgba(15,23,42,0.92)',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: '16px',
        }}>
          <div style={{
            width: '48px', height: '48px',
            border: '4px solid #334155', borderTopColor: '#3b82f6',
            borderRadius: '50%', animation: 'spin 1s linear infinite',
          }}/>
          <div style={{ fontSize: '18px', fontWeight: 700 }}>
            Running {SCENARIOS.find(s => s.key === runningKey)?.label || 'scenario'}…
          </div>
          <div style={{ fontSize: '13px', color: '#94a3b8', textAlign: 'center', maxWidth: '420px' }}>
            Scenario model → procurement orchestrator → SPR agent → digital twin.<br/>
            Local LLM inference takes 2–4 minutes. Watch the backend terminal for progress.
          </div>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Header */}
      <div style={{
        background: '#1e293b', borderBottom: '1px solid #334155',
        padding: '0 24px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', height: '60px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '20px' }}>⚡</span>
          <span style={{ fontWeight: 700, fontSize: '16px' }}>
            Energy Supply Chain Intelligence
          </span>
          <RiskBadge level={risk.level || 'UNKNOWN'} />
          {scenario?.scenario?.name && (
            <span style={{ fontSize: '12px', color: '#64748b' }}>
              Active: {scenario.scenario.name}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '12px', color: '#64748b' }}>
            Last refresh: {lastRefresh}
          </span>
          <button onClick={startTour} style={{
            background: 'transparent', color: '#60a5fa',
            border: '1px solid #1e40af', borderRadius: '8px',
            padding: '6px 14px', cursor: 'pointer', fontSize: '13px',
          }}>
            ▶ Tour
          </button>
          <button onClick={fetchAll} style={{
            background: '#3b82f6', color: '#fff', border: 'none',
            borderRadius: '8px', padding: '6px 14px',
            cursor: 'pointer', fontSize: '13px',
          }}>
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        background: '#1e293b', borderBottom: '1px solid #334155',
        padding: '0 24px', display: 'flex', gap: '4px',
      }}>
        {tabs.map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{
            background:    activeTab === tab ? '#3b82f6' : 'transparent',
            color:         activeTab === tab ? '#fff' : '#94a3b8',
            border:        'none',
            borderRadius:  '6px 6px 0 0',
            padding:       '10px 16px',
            cursor:        'pointer',
            fontSize:      '13px',
            fontWeight:    activeTab === tab ? 700 : 400,
            textTransform: 'capitalize',
          }}>
            {tab}
          </button>
        ))}
      </div>

      <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>

        {/* OVERVIEW */}
        {activeTab === 'overview' && (
          <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 280px', gap: '16px' }}>
            <div>
              <div data-tour="risk-score">
                <Card title="Master Risk Score" accent={RISK_COLORS[risk.level]}>
                  <ScoreGauge score={risk.score || 0} level={risk.level || 'UNKNOWN'} />
                  <p style={{ fontSize: '13px', color: '#94a3b8', marginTop: '12px', lineHeight: 1.5 }}>
                    {risk.executive_summary}
                  </p>
                </Card>
              </div>
              <div data-tour="commodities">
              <Card title="Commodity Prices">
                {Object.entries(commodities).map(([key, data]) => (
                  <div key={key} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '8px 0', borderBottom: '1px solid #334155',
                  }}>
                    <span style={{ fontSize: '13px', color: '#94a3b8' }}>
                      {key.replace(/_/g, ' ').toUpperCase()}
                    </span>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 700, fontSize: '14px' }}>${data.price}</div>
                      <RiskBadge level={data.risk_level} />
                    </div>
                  </div>
                ))}
              </Card>
              </div>
            </div>

            <div>
              <div data-tour="corridor-chart">
                <Card title="Corridor Risk Scores">
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={corridorChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <Tooltip
                        cursor={{ fill: 'transparent' }}
                        contentStyle={{ background: '#1e293b', border: '1px solid #334155' }}
                        labelStyle={{ color: '#f1f5f9' }}
                      />
                      <Bar dataKey="score" radius={[4, 4, 0, 0]} background={{ fill: 'transparent' }}>
                        {corridorChartData.map((entry, i) => (
                          <Cell key={i} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </div>
              <Card title="Immediate Actions Required">
                {actions.map((action, i) => {
                  const text = safeText(action);
                  return (
                    <div key={i} style={{
                      display: 'flex', gap: '10px', padding: '10px 0',
                      borderBottom: i < actions.length - 1 ? '1px solid #334155' : 'none',
                    }}>
                      <span style={{ color: '#f59e0b', fontWeight: 700 }}>→</span>
                      <span style={{ fontSize: '13px', lineHeight: 1.5 }}>{text}</span>
                    </div>
                  );
                })}
              </Card>
            </div>

            <div data-tour="watchlist">
              <Card title="Watch List" accent="#f59e0b">
                {(risk.watch_list || []).map((item, i) => (
                  <div key={i} style={{
                    padding: '8px 0', borderBottom: '1px solid #334155',
                    fontSize: '13px', display: 'flex', gap: '8px',
                  }}>
                    <span>👁</span> {safeText(item)}
                  </div>
                ))}
              </Card>
              <Card title={`Latest News (${news.total_articles || 0} articles)`}>
                <div style={{ maxHeight: '260px', overflowY: 'auto', marginRight: '-8px', paddingRight: '8px' }}>
                  {(news.sample || []).map((article, i) => (
                    <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #334155', fontSize: '12px' }}>
                      <div style={{ color: '#f1f5f9', lineHeight: 1.4 }}>{safeText(article.title)}</div>
                      <div style={{ color: '#64748b', marginTop: '2px' }}>{safeText(article.source)}</div>
                    </div>
                  ))}
                  {(news.sample || []).length === 0 && (
                    <div style={{ fontSize: '12px', color: '#64748b' }}>No articles loaded.</div>
                  )}
                </div>
                {news.total_articles > (news.sample || []).length && (
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '8px', textAlign: 'center' }}>
                    Showing {(news.sample || []).length} of {news.total_articles} — full feed in the News tab
                  </div>
                )}
              </Card>
            </div>
          </div>
        )}

        {/* MAP */}
        {activeTab === 'map' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '16px' }}>
            <div data-tour="map">
              <Card title="Live Shipping Corridor Map — Indian Ocean & Persian Gulf">
                <WorldMap corridors={corridors} />
              </Card>
            </div>
            <div data-tour="map-status">
              <Card title="Map Legend">
                {[
                  { color: '#ef4444', label: 'HIGH risk corridor' },
                  { color: '#f59e0b', label: 'MEDIUM risk corridor' },
                  { color: '#22c55e', label: 'LOW / safe route' },
                  { color: '#60a5fa', label: 'Alternative procurement' },
                ].map(item => (
                  <div key={item.label} style={{
                    display: 'flex', alignItems: 'center',
                    gap: '10px', padding: '8px 0',
                    borderBottom: '1px solid #334155',
                  }}>
                    <div style={{ width: '32px', height: '4px', background: item.color, borderRadius: '2px', flexShrink: 0 }}/>
                    <span style={{ fontSize: '13px' }}>{item.label}</span>
                  </div>
                ))}
                <div style={{ marginTop: '12px', fontSize: '12px', color: '#64748b' }}>
                  Dashed lines = disrupted corridors.<br/>
                  Colors update with live risk data.
                </div>
              </Card>

              <Card title="Corridor Status">
                {Object.entries(corridors).map(([name, data]) => (
                  <div key={name} style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', padding: '10px 0',
                    borderBottom: '1px solid #334155',
                  }}>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>
                        {name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        {data.vessels_moving}✓ {data.vessels_stopped}✗ vessels
                      </div>
                    </div>
                    <RiskBadge level={data.risk_level || 'UNKNOWN'} />
                  </div>
                ))}
              </Card>

              <Card title="Active Procurement Routes">
                {(procurement?.procurement_plan || []).slice(0, 4).map((p, i) => (
                  <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #334155', fontSize: '13px' }}>
                    <div style={{ fontWeight: 600, color: '#60a5fa' }}>{p.country}</div>
                    <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                      {p.procure_kbd} kbd — {p.delivery_days} days
                    </div>
                  </div>
                ))}
              </Card>
            </div>
          </div>
        )}

        {/* CORRIDORS */}
        {activeTab === 'corridors' && (
          <div data-tour="corridors-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {Object.entries(corridors).map(([name, data]) => (
              <div key={name} data-tour={`corridor-card-${name}`}>
              <Card title={name.replace(/_/g, ' ').toUpperCase()} accent={RISK_COLORS[data.risk_level]}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <ScoreGauge score={data.risk_score || 0} level={data.risk_level || 'UNKNOWN'} />
                  <div style={{ flex: 1, marginLeft: '20px' }}>
                    <div style={{ marginBottom: '8px' }}>
                      <span style={{ color: '#94a3b8', fontSize: '12px' }}>Vessels Moving</span>
                      <div style={{ fontWeight: 700, fontSize: '20px', color: '#22c55e' }}>{data.vessels_moving}</div>
                    </div>
                    <div>
                      <span style={{ color: '#94a3b8', fontSize: '12px' }}>Stopped/Diverted</span>
                      <div style={{ fontWeight: 700, fontSize: '20px', color: '#ef4444' }}>{data.vessels_stopped}</div>
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '8px' }}>
                  <strong style={{ color: '#f1f5f9' }}>Threat:</strong> {safeText(data.primary_threat)}
                </div>
                <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                  <strong style={{ color: '#f1f5f9' }}>Action:</strong> {safeText(data.recommendation)}
                </div>
              </Card>
              </div>
            ))}
          </div>
        )}

        {/* SCENARIO */}
        {activeTab === 'scenario' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div data-tour="scenario-buttons">
              <Card title="Trigger Scenario" accent="#7c3aed">
                <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '16px' }}>
                  Select a scenario. The system recomputes economic impact, re-ranks suppliers,
                  rebuilds the SPR drawdown plan, and refreshes the digital twin.
                </p>
                {SCENARIOS.map(sc => {
                  const isActive = scenario?.scenario_key === sc.key;
                  return (
                    <button key={sc.key} onClick={() => triggerScenario(sc.key)} disabled={triggering}
                      style={{
                        display: 'block', width: '100%',
                        background:   isActive ? '#7c3aed' : (triggering ? '#334155' : '#1e3a5f'),
                        color:        isActive ? '#fff' : (triggering ? '#64748b' : '#60a5fa'),
                        border:       `1px solid ${isActive ? '#a78bfa' : '#1d4ed8'}`,
                        borderRadius: '8px', padding: '12px 16px',
                        marginBottom: '8px', cursor: triggering ? 'not-allowed' : 'pointer',
                        textAlign: 'left', fontSize: '14px', fontWeight: 600,
                      }}>
                      {runningKey === sc.key ? '⏳ Running…' : `${isActive ? '● ' : '▶ '}${sc.label}`}
                      {isActive && (
                        <span style={{ float: 'right', fontSize: '11px', opacity: 0.8 }}>ACTIVE</span>
                      )}
                    </button>
                  );
                })}
              </Card>
            </div>
            <div data-tour="scenario-impact">
              {scenario && scenario.impact && (
                <>
                  <Card title="Active Scenario" accent="#ef4444">
                    <div style={{ fontSize: '18px', fontWeight: 700, marginBottom: '4px' }}>
                      {scenario.scenario?.name}
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '12px' }}>
                      Computed {scenario.timestamp}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                      {[
                        { label: 'Supply Cut',      value: `${fmt(scenario.scenario?.supply_cut_percent)}%` },
                        { label: 'Duration',        value: `${fmt(scenario.scenario?.duration_days)} days` },
                        { label: 'Supply Gap',      value: `${fmt(scenario.impact?.supply_gap_kbd)} kbd` },
                        { label: 'New Brent Price', value: `$${fmt(scenario.impact?.new_brent_price)}` },
                        { label: 'Total Cost',      value: `$${fmt(scenario.impact?.additional_cost_bn_usd)}B` },
                        { label: 'SPR Covers',      value: `${fmt(scenario.impact?.spr_covers_days)} days` },
                        { label: 'Days Uncovered',  value: `${fmt(scenario.impact?.gap_after_spr_days)} days` },
                        { label: 'GDP Exposure',    value: `${fmt(scenario.impact?.risk_to_gdp_percent)}%` },
                      ].map(item => (
                        <div key={item.label} style={{ background: '#0f172a', borderRadius: '8px', padding: '12px' }}>
                          <div style={{ fontSize: '11px', color: '#94a3b8' }}>{item.label}</div>
                          <div style={{ fontSize: '20px', fontWeight: 700, color: '#f59e0b' }}>{item.value}</div>
                        </div>
                      ))}
                    </div>
                    <div style={{
                      marginTop: '12px', padding: '10px',
                      background: '#0f172a', borderRadius: '8px', fontSize: '12px', color: '#94a3b8',
                    }}>
                      Refinery utilisation: {fmt(scenario.impact?.baseline_refinery_util_pct)}%
                      {' → '}
                      <strong style={{ color: '#ef4444' }}>
                        {fmt(scenario.impact?.refinery_utilisation_pct)}%
                      </strong>
                    </div>
                  </Card>
                  <Card title="Response Plan">
                    <p style={{ fontSize: '13px', lineHeight: 1.6, color: '#94a3b8', marginBottom: '16px' }}>
                      {safeText(scenario.response_plan?.situation_assessment)}
                    </p>

                    {[
                      { key: 'day_1_actions',   label: 'DAY 1 ACTIONS',   color: '#ef4444' },
                      { key: 'week_1_actions',  label: 'WEEK 1 ACTIONS',  color: '#f59e0b' },
                      { key: 'month_1_actions', label: 'MONTH 1 ACTIONS', color: '#60a5fa' },
                    ].map(group => (
                      <div key={group.key} style={{ marginBottom: '16px' }}>
                        <div style={{
                          fontSize: '11px', color: '#94a3b8', marginBottom: '8px',
                          letterSpacing: '0.08em', fontWeight: 700,
                        }}>
                          {group.label}
                        </div>
                        {(scenario.response_plan?.[group.key] || []).map((a, i) => {
                          const isObj = a && typeof a === 'object';
                          return (
                            <div key={i} style={{
                              background: '#0f172a', borderRadius: '8px',
                              padding: '12px 14px', marginBottom: '8px',
                              borderLeft: `3px solid ${group.color}`,
                            }}>
                              <div style={{ fontSize: '13px', fontWeight: 600, color: group.color }}>
                                → {safeText(a)}
                              </div>
                              {isObj && a.why && (
                                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '6px', lineHeight: 1.5 }}>
                                  <strong style={{ color: '#cbd5e1' }}>Why: </strong>{safeText(a.why)}
                                </div>
                              )}
                              {isObj && a.owner && (
                                <div style={{
                                  fontSize: '11px', color: '#64748b', marginTop: '6px',
                                  display: 'inline-block', background: '#1e293b',
                                  padding: '2px 8px', borderRadius: '999px',
                                }}>
                                  {safeText(a.owner)}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ))}

                    {scenario.response_plan?.spr_recommendation && (
                      <div style={{ padding: '10px', background: '#0f172a', borderRadius: '8px', marginBottom: '8px' }}>
                        <div style={{ fontSize: '11px', color: '#64748b' }}>SPR RECOMMENDATION</div>
                        <div style={{ fontSize: '13px', color: '#f1f5f9', marginTop: '4px', lineHeight: 1.5 }}>
                          {safeText(scenario.response_plan.spr_recommendation)}
                        </div>
                      </div>
                    )}

                    {scenario.response_plan?.key_risk && (
                      <div style={{ padding: '10px', background: '#0f172a', borderRadius: '8px', borderLeft: '3px solid #ef4444' }}>
                        <div style={{ fontSize: '11px', color: '#64748b' }}>KEY RISK</div>
                        <div style={{ fontSize: '13px', color: '#f1f5f9', marginTop: '4px', lineHeight: 1.5 }}>
                          {safeText(scenario.response_plan.key_risk)}
                        </div>
                      </div>
                    )}
                  </Card>
                </>
              )}
            </div>
          </div>
        )}

        {/* PROCUREMENT */}
        {activeTab === 'procurement' && procurement && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div data-tour="procurement-suppliers">
            <Card title="Ranked Suppliers">
              {(procurement.ranked_suppliers || []).slice(0, 6).map((s, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '12px 0', borderBottom: '1px solid #334155',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{
                      background: i === 0 ? '#f59e0b' : '#334155',
                      color:      i === 0 ? '#000' : '#94a3b8',
                      width: '28px', height: '28px', borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontWeight: 700, fontSize: '13px',
                    }}>{i + 1}</span>
                    <div>
                      <div style={{ fontWeight: 600 }}>{s.country}</div>
                      <div style={{ fontSize: '12px', color: '#94a3b8' }}>{s.grade} — {s.route}</div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        {s.refinery_count} compatible refineries
                      </div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 700, color: '#22c55e' }}>Score: {s.total_score}</div>
                    <div style={{ fontSize: '12px', color: '#94a3b8' }}>${s.actual_price}/bbl — {s.delivery_days}d</div>
                    <RiskBadge level={s.sanction_risk === 'NONE' ? 'LOW' : s.sanction_risk} />
                  </div>
                </div>
              ))}
              {(procurement.ranked_suppliers || []).length === 0 && (
                <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                  No supply gap under this scenario — no emergency procurement required.
                </div>
              )}
            </Card>
            </div>
            <div data-tour="procurement-plan">
              <Card title="Procurement Plan" accent={procurement.gap_coverage_pct >= 100 ? '#22c55e' : '#ef4444'}>
                <div style={{
                  fontSize: '32px', fontWeight: 900, marginBottom: '4px',
                  color: procurement.gap_coverage_pct >= 100 ? '#22c55e' : '#ef4444',
                }}>
                  {fmt(procurement.gap_coverage_pct)}%
                </div>
                <div style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '4px' }}>
                  Gap Coverage
                  {procurement.shortfall_kbd > 0 && (
                    <span style={{ color: '#ef4444', fontWeight: 700 }}>
                      {' '}— shortfall {procurement.shortfall_kbd} kbd
                    </span>
                  )}
                </div>
                <div style={{ color: '#64748b', fontSize: '12px', marginBottom: '16px' }}>
                  {fmt(procurement.daily_cost_mn_usd)}M/day spend · avg ${fmt(procurement.avg_price_paid)}/bbl
                  {' · '}${fmt(procurement.premium_mn_usd)}M/day premium over Brent
                </div>
                {procPlan.map((p, i) => (
                  <div key={i} style={{
                    background: '#0f172a', borderRadius: '8px', padding: '10px 14px',
                    marginBottom: '8px', display: 'flex', justifyContent: 'space-between',
                  }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{p.country}</div>
                      <div style={{ fontSize: '12px', color: '#94a3b8' }}>{p.grade} — {p.delivery_days} days</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 700, color: '#60a5fa' }}>{p.procure_kbd} kbd</div>
                      <div style={{ fontSize: '12px', color: '#94a3b8' }}>{p.covers_percent}% of gap</div>
                    </div>
                  </div>
                ))}
              </Card>
              <Card title="Executive Summary">
                <p style={{ fontSize: '13px', lineHeight: 1.6, color: '#94a3b8' }}>
                  {safeText(exec.executive_summary)}
                </p>
                <div style={{ marginTop: '12px', padding: '10px', background: '#0f172a', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>FIRST ACTION</div>
                  <div style={{ fontSize: '13px', color: '#f59e0b', marginTop: '4px' }}>
                    → {safeText(exec.first_call_to_make)}
                  </div>
                </div>
                <div style={{ marginTop: '8px', padding: '10px', background: '#0f172a', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>KEY RISK</div>
                  <div style={{ fontSize: '13px', color: '#f1f5f9', marginTop: '4px' }}>
                    {safeText(exec.key_risk)}
                  </div>
                </div>
                <div style={{ marginTop: '8px', fontSize: '12px', color: '#94a3b8' }}>
                  Confidence: <strong style={{ color: '#f1f5f9' }}>{safeText(exec.confidence)}</strong>
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* SPR */}
        {activeTab === 'spr' && spr && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div data-tour="spr-timeline">
              <Card title="SPR Drawdown Timeline">
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={sprTimeline}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis yAxisId="left"  tick={{ fill: '#f59e0b', fontSize: 11 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fill: '#ef4444', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />
                    <Line yAxisId="left"  type="monotone" dataKey="stock_kb" stroke="#f59e0b"
                          strokeWidth={2} dot={{ fill: '#f59e0b' }} name="SPR stock (thousand bbl)" />
                    <Line yAxisId="right" type="monotone" dataKey="draw_kbd" stroke="#ef4444"
                          strokeWidth={2} dot={{ fill: '#ef4444' }} name="Daily draw (kbd)" />
                  </LineChart>
                </ResponsiveContainer>
                <div style={{ fontSize: '11px', color: '#64748b', marginTop: '8px' }}>
                  Stock is a reserve level (thousand barrels). Draw is a rate (thousand barrels/day).
                </div>
              </Card>

              {sch.spr_runs_out_before_alternatives && (
                <Card accent="#ef4444">
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                    <span style={{ fontSize: '20px' }}>⚠️</span>
                    <div>
                      <div style={{ fontWeight: 700, color: '#ef4444', marginBottom: '4px' }}>
                        SPR exhausts before alternatives arrive
                      </div>
                      <div style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.5 }}>
                        Reserves run out on Day {sch.spr_exhaustion_day}, but the first cargo from{' '}
                        {spr.top_supplier} lands on Day {spr.alternative_arrival_days}.
                        {' '}<strong style={{ color: '#f1f5f9' }}>
                          {sch.days_uncovered} days of the crisis are uncovered.
                        </strong>{' '}
                        Demand-side rationing required.
                      </div>
                    </div>
                  </div>
                </Card>
              )}
            </div>

            <div data-tour="spr-status">
              <Card title="SPR Status">
                {[
                  { label: 'Total Capacity',      value: `${fmt(sch.total_stock_kb)} kb` },
                  { label: 'Available (95% fill)', value: `${fmt(sch.available_spr_kb)} kb` },
                  { label: 'Minimum Reserve',     value: `${fmt(sch.min_reserve_kb)} kb` },
                  { label: 'Usable in Crisis',    value: `${fmt(sch.usable_spr_kb)} kb` },
                  { label: 'Phase 1 Draw Rate',   value: `${fmt(sch.phase1_draw_per_day_kbd)} kbd/day` },
                  { label: 'Exhausted On',        value: `Day ${fmt(sch.spr_exhaustion_day)}` },
                  { label: 'Crisis Days Covered', value: `${fmt(sch.days_crisis_covered)} days` },
                  { label: 'Days Uncovered',      value: `${fmt(sch.days_uncovered)} days` },
                  { label: 'Replenishment Day',   value: `Day ${fmt(sch.replenishment_start_day)}` },
                ].map(item => (
                  <div key={item.label} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '8px 0', borderBottom: '1px solid #334155',
                  }}>
                    <span style={{ fontSize: '13px', color: '#94a3b8' }}>{item.label}</span>
                    <span style={{
                      fontWeight: 700,
                      color: item.label === 'Days Uncovered' && sch.days_uncovered > 0 ? '#ef4444' : '#f1f5f9',
                    }}>{item.value}</span>
                  </div>
                ))}
              </Card>
              <Card title="SPR Locations">
                {(spr.spr_config?.locations ? Object.entries(spr.spr_config.locations) : []).map(([loc, data]) => (
                  <div key={loc} style={{ padding: '10px 0', borderBottom: '1px solid #334155' }}>
                    <div style={{ fontWeight: 600 }}>{loc}</div>
                    <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                      {data.state} — {data.capacity_kb} kb
                    </div>
                  </div>
                ))}
              </Card>
              <Card title="Policy Recommendation" accent="#7c3aed">
                <p style={{ fontSize: '13px', lineHeight: 1.6, color: '#94a3b8' }}>
                  {safeText(spr.policy?.policy_recommendation)}
                </p>
                <div style={{ marginTop: '12px' }}>
                  <span style={{ fontSize: '12px', color: '#94a3b8' }}>Approval: </span>
                  <span style={{ fontWeight: 700, color: '#ef4444' }}>{safeText(spr.policy?.approval_urgency)}</span>
                </div>
                <div style={{ marginTop: '8px', fontSize: '12px', color: '#94a3b8', lineHeight: 1.5 }}>
                  <strong style={{ color: '#f1f5f9' }}>If delayed:</strong> {safeText(spr.policy?.risk_if_delayed)}
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* NEWS */}
        {activeTab === 'news' && (
          <div data-tour="news-feed" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <Card title={`News Intelligence — ${news.total_articles || 0} articles monitored`}>
              <div style={{ maxHeight: '520px', overflowY: 'auto', marginRight: '-8px', paddingRight: '8px' }}>
                {(news.sample || []).map((article, i) => (
                  <div key={i} style={{ padding: '12px 0', borderBottom: '1px solid #334155' }}>
                    <div style={{ fontSize: '14px', fontWeight: 500, lineHeight: 1.4 }}>{safeText(article.title)}</div>
                    <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>{safeText(article.source)}</div>
                  </div>
                ))}
                {(news.sample || []).length === 0 && (
                  <div style={{ fontSize: '13px', color: '#64748b' }}>No articles loaded.</div>
                )}
              </div>
            </Card>
            <Card title="Geopolitical Watch">
              {(risk.watch_list || []).map((item, i) => (
                <div key={i} style={{
                  padding: '14px', background: '#0f172a', borderRadius: '8px',
                  marginBottom: '8px', fontSize: '14px', display: 'flex', gap: '10px',
                }}>
                  <span>👁</span> {safeText(item)}
                </div>
              ))}
              <div style={{ marginTop: '16px' }}>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '8px' }}>ACTIVE SANCTIONS</div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: '#ef4444' }}>
                  4 active sanctions affecting oil supply
                </div>
                <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>
                  Iran (CRITICAL) · Russia (HIGH) · Venezuela (MEDIUM) · Syria (LOW)
                </div>
              </div>
            </Card>
          </div>
        )}

      </div>
    </div>
  );
}