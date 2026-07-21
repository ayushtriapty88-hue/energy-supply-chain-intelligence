import React, { useState, useEffect, useRef } from 'react';

// Steps run in TAB ORDER (left to right), grouped so all steps on a tab
// finish before the tour moves to the next tab — no jumping back and forth.
export const TOUR_STEPS = [
  // ---- OVERVIEW ----
  {
    tab: 'overview',
    selector: '[data-tour="risk-score"]',
    title: 'Master Risk Score',
    body: 'The headline number, 0-100, fusing live vessel tracking, commodity prices, and news sentiment into one figure every decision-maker checks first.',
  },
  {
    tab: 'overview',
    selector: '[data-tour="commodities"]',
    title: 'Live Commodity Prices',
    body: 'Brent, WTI, and natural gas, each with its own risk flag. A price spike here is often the first quantitative sign of a supply shock.',
  },
  {
    tab: 'overview',
    selector: '[data-tour="corridor-chart"]',
    title: 'Corridor Risk Breakdown',
    body: 'The four chokepoints India depends on, scored live. Red means disrupted; green means a safe alternative route.',
  },
  {
    tab: 'overview',
    selector: '[data-tour="watchlist"]',
    title: 'Watch List & News',
    body: 'The signals the AI is tracking right now, plus the live news feed driving the scores - so you can see the reasoning behind the numbers.',
  },

  // ---- MAP ----
  {
    tab: 'map',
    selector: '[data-tour="map"]',
    title: 'Live Corridor Map',
    body: 'The whole picture on one map - disrupted corridors in red, safe routes in green, and every alternative supplier plotted with its available volume.',
  },
  {
    tab: 'map',
    selector: '[data-tour="map-status"]',
    title: 'Corridor & Route Status',
    body: 'A running tally of vessels moving versus stopped in each corridor, and the alternative procurement routes currently in play.',
  },

  // ---- CORRIDORS (one step per chokepoint) ----
  {
    tab: 'corridors',
    selector: '[data-tour="corridor-card-strait_of_hormuz"]',
    title: 'Corridor: Strait of Hormuz',
    body: 'The most critical chokepoint - ~45% of India\'s crude transits here. This card shows its live risk score, vessels moving vs diverted, the AI-identified threat, and the recommended action.',
  },
  {
    tab: 'corridors',
    selector: '[data-tour="corridor-card-red_sea"]',
    title: 'Corridor: Red Sea',
    body: 'The Suez-to-Bab-el-Mandeb route, exposed to Houthi attacks. If it closes, tankers divert around the Cape of Good Hope - adding 10-14 days.',
  },
  {
    tab: 'corridors',
    selector: '[data-tour="corridor-card-suez_canal"]',
    title: 'Corridor: Suez Canal',
    body: 'Carries ~12% of global trade. A blockage here ripples through oil markets worldwide - the AI tracks its status and flags escalation.',
  },
  {
    tab: 'corridors',
    selector: '[data-tour="corridor-card-cape_of_good_hope"]',
    title: 'Corridor: Cape of Good Hope',
    body: 'The safe fallback route around Africa. Longer and costlier, but open water with no chokepoint risk - the system routes here when others are disrupted.',
  },

  // ---- SCENARIO ----
  {
    tab: 'scenario',
    selector: '[data-tour="scenario-buttons"]',
    title: 'Trigger a Disruption',
    body: 'Click any scenario - a full Hormuz closure, a Russia embargo - and five AI agents recompute the entire response chain in real time.',
  },
  {
    tab: 'scenario',
    selector: '[data-tour="scenario-impact"]',
    title: 'Instant Economic Impact',
    body: 'Supply gap, new Brent price, GDP exposure, refinery utilisation - all computed deterministically, then explained in plain language by the AI.',
  },

  // ---- PROCUREMENT ----
  {
    tab: 'procurement',
    selector: '[data-tour="procurement-suppliers"]',
    title: 'Ranked Suppliers',
    body: 'Every alternative supplier scored on price, delivery time, sanctions risk, and refinery-grade compatibility - the highest score is your best bet.',
  },
  {
    tab: 'procurement',
    selector: '[data-tour="procurement-plan"]',
    title: 'Adaptive Procurement Plan',
    body: 'The system builds a mix of suppliers to close the gap, showing coverage %, daily cost, and any shortfall that still needs demand-side action.',
  },

  // ---- SPR ----
  {
    tab: 'spr',
    selector: '[data-tour="spr-timeline"]',
    title: 'SPR Drawdown Timeline',
    body: 'A day-by-day view of the strategic reserve draining against the crisis - the point where the stock line hits zero is the moment of truth.',
  },
  {
    tab: 'spr',
    selector: '[data-tour="spr-status"]',
    title: 'Reserve Status & Policy',
    body: 'Exactly when reserves run out versus when alternative cargo arrives, plus the AI-drafted policy recommendation for the petroleum ministry.',
  },

  // ---- NEWS ----
  {
    tab: 'news',
    selector: '[data-tour="news-feed"]',
    title: 'News & Sanctions Intelligence',
    body: 'The full monitored news feed and the active sanctions map - the raw geopolitical inputs feeding every score across the dashboard.',
  },
];

export default function GuidedTour({ steps, stepIndex, onNext, onBack, onFinish }) {
  const step = steps[stepIndex];
  const [rect, setRect] = useState(null);
  const [searching, setSearching] = useState(true);
  const pollRef = useRef(null);

  useEffect(() => {
    if (!step) return;
    setRect(null);
    setSearching(true);

    let attempts = 0;
    const maxAttempts = 25;        // 25 x 100ms = 2.5s
    let scrolled = false;

    const tick = () => {
      const el = document.querySelector(step.selector);
      if (el) {
        if (!scrolled) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          scrolled = true;
        }
        setRect(el.getBoundingClientRect());
        setSearching(false);
      } else {
        attempts += 1;
        if (attempts >= maxAttempts) setSearching(false);
      }
    };

    tick();
    pollRef.current = setInterval(tick, 100);
    return () => clearInterval(pollRef.current);
  }, [step, stepIndex]);

  useEffect(() => {
    const reMeasure = () => {
      if (!step) return;
      const el = document.querySelector(step.selector);
      if (el) setRect(el.getBoundingClientRect());
    };
    window.addEventListener('resize', reMeasure);
    window.addEventListener('scroll', reMeasure, true);
    return () => {
      window.removeEventListener('resize', reMeasure);
      window.removeEventListener('scroll', reMeasure, true);
    };
  }, [step]);

  if (!step) return null;

  const pad = 8;
  const spot = rect ? {
    top: rect.top - pad, left: rect.left - pad,
    width: rect.width + pad * 2, height: rect.height + pad * 2,
  } : null;

  const isLast = stepIndex === steps.length - 1;

  // Put the tooltip OPPOSITE the highlighted element so it never covers it.
  // If the spotlight sits in the lower half of the screen, pin the tooltip to
  // the top; otherwise pin it to the bottom.
  const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
  const spotCenterY = spot ? spot.top + spot.height / 2 : vh / 2;
  const tooltipAtTop = spotCenterY > vh / 2;

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 10001, pointerEvents: 'none' }}>
      {spot ? (
        <div style={{
          position: 'fixed',
          top: spot.top, left: spot.left,
          width: spot.width, height: spot.height,
          borderRadius: '12px',
          boxShadow: '0 0 0 9999px rgba(6,11,24,0.78)',
          border: '2px solid #3b82f6',
          transition: 'all 0.3s cubic-bezier(0.4,0,0.2,1)',
          pointerEvents: 'none',
        }}/>
      ) : (
        <div style={{
          position: 'fixed', inset: 0,
          background: 'rgba(6,11,24,0.78)',
          pointerEvents: 'none',
        }}/>
      )}

      <div style={{
        position: 'fixed',
        ...(tooltipAtTop ? { top: '24px' } : { bottom: '32px' }),
        left: '50%',
        transform: 'translateX(-50%)',
        width: '400px', maxWidth: '90vw',
        pointerEvents: 'auto',
        background: '#1e293b', border: '1px solid #3b82f6',
        borderRadius: '12px', padding: '18px 20px',
        boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
        color: '#f1f5f9', fontFamily: "'Inter', sans-serif",
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: '10px',
        }}>
          <span style={{
            fontSize: '11px', color: '#60a5fa', fontWeight: 700,
            letterSpacing: '0.08em',
          }}>
            {step.tab.toUpperCase()} · STEP {stepIndex + 1} OF {steps.length}
          </span>
          <button onClick={onFinish} style={{
            background: 'none', border: 'none', color: '#94a3b8',
            cursor: 'pointer', fontSize: '12px', fontWeight: 600,
          }}>
            Skip tour X
          </button>
        </div>

        <div style={{ fontSize: '16px', fontWeight: 700, marginBottom: '8px' }}>
          {step.title}
        </div>
        <div style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6, marginBottom: '4px' }}>
          {step.body}
        </div>
        {searching && (
          <div style={{ fontSize: '11px', color: '#60a5fa', marginBottom: '12px' }}>
            Locating on screen...
          </div>
        )}
        {!searching && !spot && (
          <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '12px', fontStyle: 'italic' }}>
            (This panel appears once its data loads.)
          </div>
        )}
        {!searching && spot && <div style={{ marginBottom: '12px' }} />}

        <div style={{ display: 'flex', gap: '4px', marginBottom: '16px' }}>
          {steps.map((_, i) => (
            <div key={i} style={{
              height: '4px', flex: 1, borderRadius: '2px',
              background: i <= stepIndex ? '#3b82f6' : '#334155',
              transition: 'background 0.3s',
            }}/>
          ))}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
          <button onClick={onBack} disabled={stepIndex === 0} style={{
            background: 'transparent', color: stepIndex === 0 ? '#475569' : '#94a3b8',
            border: '1px solid #334155', borderRadius: '8px',
            padding: '9px 18px', fontSize: '13px',
            cursor: stepIndex === 0 ? 'not-allowed' : 'pointer',
          }}>
            &larr; Back
          </button>
          <button onClick={isLast ? onFinish : onNext} style={{
            background: '#3b82f6', color: '#fff', border: 'none',
            borderRadius: '8px', padding: '9px 24px',
            fontSize: '13px', fontWeight: 700, cursor: 'pointer',
          }}>
            {isLast ? 'Finish' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
}