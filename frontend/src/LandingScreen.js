import React from 'react';

export default function LandingScreen({ onEnter, onTour }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 10000,
      background: 'radial-gradient(circle at 30% 20%, #1e293b 0%, #0f172a 55%, #060b18 100%)',
      color: '#f1f5f9', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      fontFamily: "'Inter', -apple-system, sans-serif", padding: '24px',
      animation: 'landingFade 0.6s ease',
    }}>
      <style>{`
        @keyframes landingFade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes floatUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulseDot { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
      `}</style>

      <div style={{ animation: 'floatUp 0.7s ease 0.1s both', textAlign: 'center', maxWidth: '760px' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          background: 'rgba(59,130,246,0.1)', border: '1px solid #1e40af',
          borderRadius: '999px', padding: '6px 16px', fontSize: '12px',
          color: '#60a5fa', marginBottom: '28px', letterSpacing: '0.05em',
        }}>
          <span style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: '#22c55e', animation: 'pulseDot 1.6s infinite',
          }}/>
          LIVE · AI-POWERED · RUNS FULLY LOCAL
        </div>

        <div style={{ fontSize: '64px', marginBottom: '8px' }}>⚡</div>

        <h1 style={{
          fontSize: '46px', fontWeight: 900, margin: '0 0 16px',
          background: 'linear-gradient(120deg, #f1f5f9 0%, #60a5fa 100%)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          lineHeight: 1.1,
        }}>
          Energy Supply Chain Intelligence
        </h1>

        <p style={{
          fontSize: '18px', color: '#94a3b8', lineHeight: 1.6,
          margin: '0 auto 12px', maxWidth: '620px',
        }}>
          A real-time command centre for India's crude oil security. It watches shipping
          corridors, prices, and geopolitics — then simulates disruptions and generates
          procurement, SPR, and policy responses automatically.
        </p>

        <p style={{ fontSize: '14px', color: '#64748b', marginBottom: '36px' }}>
          India imports <strong style={{ color: '#f59e0b' }}>88%</strong> of its crude, and{' '}
          <strong style={{ color: '#f59e0b' }}>45%</strong> of it passes through the Strait of Hormuz.
          When that corridor closes, this system already has the answer.
        </p>
      </div>

      <div style={{
        display: 'flex', gap: '32px', marginBottom: '40px', flexWrap: 'wrap',
        justifyContent: 'center', animation: 'floatUp 0.7s ease 0.25s both',
      }}>
        {[
          { icon: '🛰️', title: '4 Corridors', sub: 'Live vessel tracking' },
          { icon: '🤖', title: '5 AI Agents', sub: 'Autonomous analysis' },
          { icon: '📉', title: '5 Scenarios', sub: 'Disruption modelling' },
          { icon: '🧠', title: 'RAG Memory', sub: 'Historical precedent' },
        ].map(f => (
          <div key={f.title} style={{ textAlign: 'center', minWidth: '120px' }}>
            <div style={{ fontSize: '28px', marginBottom: '6px' }}>{f.icon}</div>
            <div style={{ fontSize: '15px', fontWeight: 700 }}>{f.title}</div>
            <div style={{ fontSize: '12px', color: '#64748b' }}>{f.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '14px', animation: 'floatUp 0.7s ease 0.4s both' }}>
        <button onClick={onTour} style={{
          background: 'linear-gradient(120deg, #3b82f6, #2563eb)', color: '#fff',
          border: 'none', borderRadius: '10px', padding: '15px 32px',
          fontSize: '15px', fontWeight: 700, cursor: 'pointer',
          boxShadow: '0 8px 24px rgba(37,99,235,0.4)',
        }}>
          ▶ Take the guided tour
        </button>
        <button onClick={onEnter} style={{
          background: 'transparent', color: '#94a3b8',
          border: '1px solid #334155', borderRadius: '10px',
          padding: '15px 32px', fontSize: '15px', fontWeight: 600, cursor: 'pointer',
        }}>
          Skip to dashboard →
        </button>
      </div>
    </div>
  );
}