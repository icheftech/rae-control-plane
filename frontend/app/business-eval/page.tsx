'use client';

import { useState, useCallback } from 'react';
import axios from 'axios';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ScrapedListing {
  success: boolean;
  error?: string;
  title?: string;
  asking_price?: number;
  revenue?: number;
  cash_flow?: number;
  location?: string;
  industry?: string;
  description?: string;
}

interface ScoreBreakdown {
  cf_multiple_pts: number;
  cf_multiple_max: number;
  dscr_pts: number;
  dscr_max: number;
  payback_pts: number;
  payback_max: number;
  cf_margin_pts: number;
  cf_margin_max: number;
}

interface DealMetrics {
  asking_price: number;
  revenue: number;
  cash_flow: number;
  adjusted_cash_flow: number;
  cf_multiple: number;
  revenue_multiple: number;
  cf_margin_pct: number;
  industry: string;
  industry_cf_multiple: number;
  industry_revenue_multiple: number;
  industry_cf_margin_pct: number;
  industry_default_rate_pct: number;
  down_payment: number;
  sba_guaranty_fee: number;
  total_acquisition_cost: number;
  total_cash_down: number;
  total_debt: number;
  monthly_payment: number;
  annual_payment: number;
  dscr: number;
  payback_years: number;
  net_annual_cf_after_debt: number;
  score: number;
  grade: string;
  grade_label: string;
  score_breakdown: ScoreBreakdown;
  deal_summary: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const INDUSTRIES = [
  'General',
  'Laundromats and Coin Laundry',
  'Restaurants',
  'Retail',
  'Auto Repair',
  'Gas Stations / Convenience Stores',
  'Hair Salons / Barber Shops',
  'Car Washes',
  'Dry Cleaners',
  'Medical / Dental Practices',
  'E-Commerce',
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.replace('/v1', '') || 'http://localhost:8000/api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt$(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

function fmtNum(n: number, decimals = 2): string {
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function gradeColor(grade: string): string {
  const map: Record<string, string> = { A: '#16a34a', B: '#65a30d', C: '#d97706', D: '#ea580c', F: '#dc2626' };
  return map[grade] ?? '#6b7280';
}

function gradeBg(grade: string): string {
  const map: Record<string, string> = { A: '#dcfce7', B: '#ecfccb', C: '#fef3c7', D: '#ffedd5', F: '#fee2e2' };
  return map[grade] ?? '#f3f4f6';
}

function parseInput(val: string): number {
  return parseFloat(val.replace(/[^0-9.]/g, '')) || 0;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MetricCard({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div
      style={{
        background: highlight ? '#eff6ff' : '#fff',
        border: `1px solid ${highlight ? '#bfdbfe' : '#e5e7eb'}`,
        borderRadius: 10,
        padding: '16px 18px',
      }}
    >
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4, fontWeight: 500 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: highlight ? '#1d4ed8' : '#111827' }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

function ScoreBar({ pts, max, label }: { pts: number; max: number; label: string }) {
  const pct = Math.round((pts / max) * 100);
  const color = pct >= 75 ? '#16a34a' : pct >= 50 ? '#d97706' : '#dc2626';
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#374151', marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ fontWeight: 600 }}>{pts}/{max}</span>
      </div>
      <div style={{ background: '#e5e7eb', borderRadius: 99, height: 8, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, background: color, height: '100%', borderRadius: 99, transition: 'width 0.6s ease' }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function BusinessEvalPage() {
  const [url, setUrl] = useState('');
  const [scraping, setScraping] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState('');

  const [title, setTitle] = useState('');
  const [askingPrice, setAskingPrice] = useState('');
  const [revenue, setRevenue] = useState('');
  const [cashFlow, setCashFlow] = useState('');
  const [industry, setIndustry] = useState('General');
  const [financingType, setFinancingType] = useState<'SBA' | 'Custom'>('SBA');
  const [rate, setRate] = useState('10.0');
  const [term, setTerm] = useState('10');
  const [downPct, setDownPct] = useState('10');
  const [sellerFinancing, setSellerFinancing] = useState('0');
  const [additionalExpenses, setAdditionalExpenses] = useState('0');

  const [calculating, setCalculating] = useState(false);
  const [results, setResults] = useState<DealMetrics | null>(null);
  const [calcError, setCalcError] = useState('');

  // Fetch listing from URL
  const handleFetch = useCallback(async () => {
    if (!url.trim()) return;
    setScraping(true);
    setScrapeMsg('');
    setResults(null);

    try {
      const { data } = await axios.post<ScrapedListing>(`${API_BASE}/business-eval/scrape`, { url });

      if (data.title) setTitle(data.title);
      if (data.asking_price) setAskingPrice(String(data.asking_price));
      if (data.revenue) setRevenue(String(data.revenue));
      if (data.cash_flow) setCashFlow(String(data.cash_flow));
      if (data.industry) setIndustry(data.industry);

      if (data.error) {
        setScrapeMsg(data.error);
      } else if (!data.asking_price && !data.revenue && !data.cash_flow) {
        setScrapeMsg('No financial data found — please enter values manually.');
      } else {
        setScrapeMsg('Listing data loaded. Review the fields below and click Calculate.');
      }
    } catch {
      setScrapeMsg('Could not reach the server. Enter values manually.');
    } finally {
      setScraping(false);
    }
  }, [url]);

  // Calculate
  const handleCalculate = useCallback(async () => {
    setCalcError('');
    const ap = parseInput(askingPrice);
    const rev = parseInput(revenue);
    const cf = parseInput(cashFlow);

    if (!ap || !rev || !cf) {
      setCalcError('Asking Price, Revenue, and Cash Flow are required.');
      return;
    }

    setCalculating(true);
    try {
      const { data } = await axios.post<DealMetrics>(`${API_BASE}/business-eval/calculate`, {
        asking_price: ap,
        revenue: rev,
        cash_flow: cf,
        industry,
        financing_type: financingType,
        rate_pct: parseFloat(rate) || 10,
        term_years: parseInt(term) || 10,
        down_payment_pct: parseFloat(downPct) || 10,
        seller_financing: parseInput(sellerFinancing),
        additional_expenses: parseInput(additionalExpenses),
      });
      setResults(data);
      setTimeout(() => document.getElementById('results-section')?.scrollIntoView({ behavior: 'smooth' }), 100);
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail || e.message : 'Calculation error';
      setCalcError(String(msg));
    } finally {
      setCalculating(false);
    }
  }, [askingPrice, revenue, cashFlow, industry, financingType, rate, term, downPct, sellerFinancing, additionalExpenses]);

  const handleClear = () => {
    setUrl(''); setTitle(''); setAskingPrice(''); setRevenue(''); setCashFlow('');
    setIndustry('General'); setFinancingType('SBA'); setRate('10.0'); setTerm('10');
    setDownPct('10'); setSellerFinancing('0'); setAdditionalExpenses('0');
    setResults(null); setScrapeMsg(''); setCalcError('');
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '10px 12px', border: '1px solid #d1d5db',
    borderRadius: 8, fontSize: 14, outline: 'none', boxSizing: 'border-box',
    background: '#fff', color: '#111827',
  };

  const labelStyle: React.CSSProperties = { fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 5 };

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', fontFamily: 'Inter, system-ui, sans-serif' }}>

      {/* Header */}
      <div style={{ background: '#1e3a5f', padding: '16px 24px', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ background: '#3b82f6', borderRadius: 8, width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ color: '#fff', fontSize: 18, fontWeight: 700 }}>$</span>
        </div>
        <div>
          <div style={{ color: '#fff', fontWeight: 700, fontSize: 18 }}>Business Deal Evaluator</div>
          <div style={{ color: '#93c5fd', fontSize: 12 }}>Paste a BizBuySell URL or enter values manually</div>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <a href="/" style={{ color: '#93c5fd', fontSize: 13, textDecoration: 'none' }}>← SSO Dashboard</a>
        </div>
      </div>

      <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 16px' }}>

        {/* URL fetch */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 20, marginBottom: 20 }}>
          <label style={{ ...labelStyle, fontSize: 14 }}>BizBuySell Listing URL</label>
          <div style={{ display: 'flex', gap: 10 }}>
            <input
              style={{ ...inputStyle, flex: 1 }}
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://www.bizbuysell.com/business-opportunity/..."
              onKeyDown={e => e.key === 'Enter' && handleFetch()}
            />
            <button
              onClick={handleFetch}
              disabled={scraping || !url.trim()}
              style={{
                padding: '10px 20px', background: scraping || !url.trim() ? '#93c5fd' : '#2563eb',
                color: '#fff', border: 'none', borderRadius: 8, cursor: scraping || !url.trim() ? 'not-allowed' : 'pointer',
                fontWeight: 600, fontSize: 14, whiteSpace: 'nowrap',
              }}
            >
              {scraping ? 'Fetching…' : 'Fetch Listing'}
            </button>
          </div>
          {scrapeMsg && (
            <div style={{
              marginTop: 10, padding: '10px 14px', borderRadius: 8, fontSize: 13,
              background: scrapeMsg.includes('loaded') ? '#f0fdf4' : '#fffbeb',
              color: scrapeMsg.includes('loaded') ? '#166534' : '#92400e',
              border: `1px solid ${scrapeMsg.includes('loaded') ? '#bbf7d0' : '#fde68a'}`,
            }}>
              {scrapeMsg}
            </div>
          )}
          {title && (
            <div style={{ marginTop: 10, fontWeight: 600, color: '#1e3a5f', fontSize: 15 }}>{title}</div>
          )}
        </div>

        {/* Form */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 20 }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#1e3a5f', marginBottom: 16 }}>Business Financials</div>

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Industry</label>
                <select value={industry} onChange={e => setIndustry(e.target.value)} style={inputStyle}>
                  {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Asking Price <span style={{ color: '#ef4444' }}>*</span></label>
                <input style={inputStyle} value={askingPrice} onChange={e => setAskingPrice(e.target.value)} placeholder="e.g. 186000" />
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Annual Revenue <span style={{ color: '#ef4444' }}>*</span></label>
                <input style={inputStyle} value={revenue} onChange={e => setRevenue(e.target.value)} placeholder="e.g. 276000" />
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Cash Flow (SDE) <span style={{ color: '#ef4444' }}>*</span></label>
                <input style={inputStyle} value={cashFlow} onChange={e => setCashFlow(e.target.value)} placeholder="e.g. 80000" />
              </div>

              <div>
                <label style={labelStyle}>Additional Annual Expenses</label>
                <input style={inputStyle} value={additionalExpenses} onChange={e => setAdditionalExpenses(e.target.value)} placeholder="e.g. 5000" />
              </div>
            </div>

          </div>

          {/* Right column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 20 }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#1e3a5f', marginBottom: 16 }}>Financing</div>

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Financing Type</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {(['SBA', 'Custom'] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => {
                        setFinancingType(t);
                        if (t === 'SBA') { setRate('10.0'); setTerm('10'); setDownPct('10'); }
                      }}
                      style={{
                        flex: 1, padding: '9px 0', border: `2px solid ${financingType === t ? '#2563eb' : '#d1d5db'}`,
                        borderRadius: 8, background: financingType === t ? '#eff6ff' : '#fff',
                        color: financingType === t ? '#1d4ed8' : '#374151',
                        fontWeight: financingType === t ? 700 : 400, cursor: 'pointer', fontSize: 14,
                      }}
                    >
                      {t === 'SBA' ? 'SBA Loan' : 'Custom Loan'}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                <div>
                  <label style={labelStyle}>Interest Rate (%)</label>
                  <input style={inputStyle} value={rate} onChange={e => setRate(e.target.value)} />
                </div>
                <div>
                  <label style={labelStyle}>Term (years)</label>
                  <input style={inputStyle} value={term} onChange={e => setTerm(e.target.value)} />
                </div>
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Down Payment (%)</label>
                <input style={inputStyle} value={downPct} onChange={e => setDownPct(e.target.value)} />
              </div>

              <div>
                <label style={labelStyle}>Seller Financing ($)</label>
                <input style={inputStyle} value={sellerFinancing} onChange={e => setSellerFinancing(e.target.value)} placeholder="0" />
              </div>
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={handleCalculate}
                disabled={calculating}
                style={{
                  flex: 1, padding: '13px 0', background: calculating ? '#93c5fd' : '#1e3a5f',
                  color: '#fff', border: 'none', borderRadius: 10, cursor: calculating ? 'not-allowed' : 'pointer',
                  fontWeight: 700, fontSize: 15,
                }}
              >
                {calculating ? 'Calculating…' : 'Calculate Deal'}
              </button>
              <button
                onClick={handleClear}
                style={{
                  padding: '13px 20px', background: '#fff', color: '#6b7280',
                  border: '1px solid #d1d5db', borderRadius: 10, cursor: 'pointer', fontWeight: 600, fontSize: 15,
                }}
              >
                Clear
              </button>
            </div>

            {calcError && (
              <div style={{ padding: '12px 14px', background: '#fee2e2', color: '#b91c1c', borderRadius: 8, fontSize: 13 }}>
                {calcError}
              </div>
            )}

          </div>
        </div>

        {/* Results */}
        {results && (
          <div id="results-section" style={{ marginTop: 28 }}>

            {/* Score banner */}
            <div style={{
              background: gradeBg(results.grade),
              border: `2px solid ${gradeColor(results.grade)}`,
              borderRadius: 16, padding: '24px 28px', marginBottom: 20,
              display: 'flex', alignItems: 'center', gap: 28, flexWrap: 'wrap',
            }}>
              <div style={{ textAlign: 'center', minWidth: 90 }}>
                <div style={{
                  width: 80, height: 80, borderRadius: '50%',
                  background: gradeColor(results.grade),
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 6px',
                }}>
                  <span style={{ color: '#fff', fontSize: 30, fontWeight: 800 }}>{results.grade}</span>
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, color: gradeColor(results.grade) }}>{results.grade_label}</div>
              </div>

              <div style={{ flex: 1, minWidth: 220 }}>
                <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>Deal Score</div>
                <div style={{ fontSize: 38, fontWeight: 800, color: gradeColor(results.grade), lineHeight: 1 }}>{results.score}</div>
                <div style={{ fontSize: 12, color: '#9ca3af' }}>out of 100</div>
                <div style={{ background: '#e5e7eb', borderRadius: 99, height: 8, marginTop: 10, overflow: 'hidden', maxWidth: 280 }}>
                  <div style={{ width: `${results.score}%`, background: gradeColor(results.grade), height: '100%', borderRadius: 99 }} />
                </div>
              </div>

              <div style={{ flex: 2, minWidth: 260 }}>
                <div style={{ fontSize: 13, fontStyle: 'italic', color: '#374151', lineHeight: 1.6 }}>
                  {results.deal_summary}
                </div>
              </div>
            </div>

            {/* Score breakdown */}
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 20, marginBottom: 20 }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#1e3a5f', marginBottom: 16 }}>Score Breakdown</div>
              <ScoreBar pts={results.score_breakdown.cf_multiple_pts} max={results.score_breakdown.cf_multiple_max} label="Cash Flow Multiple" />
              <ScoreBar pts={results.score_breakdown.dscr_pts} max={results.score_breakdown.dscr_max} label="DSCR (Debt Coverage)" />
              <ScoreBar pts={results.score_breakdown.payback_pts} max={results.score_breakdown.payback_max} label="Payback Period" />
              <ScoreBar pts={results.score_breakdown.cf_margin_pts} max={results.score_breakdown.cf_margin_max} label="Cash Flow Margin" />
            </div>

            {/* Metrics grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 20 }}>
              <MetricCard label="Asking Price" value={fmt$(results.asking_price)} sub={`Industry avg multiple: ${results.industry_cf_multiple}x`} />
              <MetricCard label="Annual Revenue" value={fmt$(results.revenue)} sub={`Industry avg multiple: ${results.industry_revenue_multiple}x`} />
              <MetricCard label="Cash Flow (SDE)" value={fmt$(results.cash_flow)} sub={results.adjusted_cash_flow !== results.cash_flow ? `Adjusted: ${fmt$(results.adjusted_cash_flow)}` : undefined} />
              <MetricCard label="Cash Flow Multiple" value={`${fmtNum(results.cf_multiple)}x`} sub={`Industry avg: ${results.industry_cf_multiple}x`} highlight={results.cf_multiple < results.industry_cf_multiple} />
              <MetricCard label="Revenue Multiple" value={`${fmtNum(results.revenue_multiple)}x`} sub={`Industry avg: ${results.industry_revenue_multiple}x`} highlight={results.revenue_multiple < results.industry_revenue_multiple} />
              <MetricCard label="Cash Flow Margin" value={`${fmtNum(results.cf_margin_pct, 1)}%`} sub={`Industry avg: ${results.industry_cf_margin_pct}%`} highlight={results.cf_margin_pct >= results.industry_cf_margin_pct} />
              <MetricCard label="DSCR" value={results.dscr >= 99 ? 'N/A' : fmtNum(results.dscr)} sub={results.dscr >= 1.25 ? 'Meets SBA minimum' : 'Below SBA minimum (1.25)'} highlight={results.dscr >= 1.5} />
              <MetricCard label="Industry Default Rate" value={`${results.industry_default_rate_pct}%`} sub={results.industry} />
            </div>

            {/* Financing grid */}
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 20, marginBottom: 20 }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#1e3a5f', marginBottom: 16 }}>Financing Details</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
                <MetricCard label="Total Acquisition Cost" value={fmt$(results.total_acquisition_cost)} />
                <MetricCard label="Total Cash Down" value={fmt$(results.total_cash_down)} />
                <MetricCard label="Total Debt" value={fmt$(results.total_debt)} />
                <MetricCard label="Monthly Payment" value={fmt$(results.monthly_payment)} />
                <MetricCard label="Annual Debt Service" value={fmt$(results.annual_payment)} />
                <MetricCard label="Net Annual CF After Debt" value={fmt$(results.net_annual_cf_after_debt)} highlight={results.net_annual_cf_after_debt > 0} />
                <MetricCard label="Est. Payback Period" value={results.payback_years >= 99 ? 'N/A' : `${fmtNum(results.payback_years, 1)} yrs`} sub="Cash down ÷ cash flow" />
                {results.sba_guaranty_fee > 0 && <MetricCard label="SBA Guaranty Fee" value={fmt$(results.sba_guaranty_fee)} />}
              </div>
            </div>

            {/* Scoring guide */}
            <div style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 12, padding: 20 }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: '#374151', marginBottom: 12 }}>Scoring Guide</div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {[
                  { grade: 'A', range: '85–100', label: 'Excellent Deal' },
                  { grade: 'B', range: '70–84', label: 'Good Deal' },
                  { grade: 'C', range: '55–69', label: 'Fair Deal' },
                  { grade: 'D', range: '40–54', label: 'Risky Deal' },
                  { grade: 'F', range: '< 40', label: 'Pass on This' },
                ].map(item => (
                  <div key={item.grade} style={{
                    display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px',
                    background: gradeBg(item.grade), borderRadius: 99,
                    border: `1px solid ${gradeColor(item.grade)}22`,
                  }}>
                    <span style={{ fontWeight: 700, color: gradeColor(item.grade) }}>{item.grade}</span>
                    <span style={{ fontSize: 12, color: '#6b7280' }}>{item.range} — {item.label}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 12, fontSize: 12, color: '#9ca3af', lineHeight: 1.6 }}>
                Scores are based on: Cash Flow Multiple (25 pts), DSCR (30 pts), Payback Period (25 pts), CF Margin (20 pts).
                This tool is for informational purposes only — always perform full due diligence before purchasing a business.
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
