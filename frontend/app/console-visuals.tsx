import { Activity, Box, CheckCircle2, CirclePlay, Database, Shield } from 'lucide-react';
import { Row } from '@/lib/api';

export function Globe() {
  return <div className="globe-art" aria-hidden="true"><svg viewBox="0 0 600 420">
    <defs>
      <radialGradient id="ocean" cx="32%" cy="24%"><stop stopColor="#17629a"/><stop offset=".52" stopColor="#073051"/><stop offset="1" stopColor="#010e1b"/></radialGradient>
      <radialGradient id="halo"><stop stopColor="#00aaff" stopOpacity=".22"/><stop offset="1" stopColor="#00aaff" stopOpacity="0"/></radialGradient>
      <linearGradient id="land" x2="1" y2="1"><stop stopColor="#74acc7"/><stop offset="1" stopColor="#194865"/></linearGradient>
      <clipPath id="sphere"><circle cx="300" cy="205" r="150"/></clipPath>
      <filter id="glow"><feGaussianBlur stdDeviation="3"/></filter>
    </defs>
    <ellipse cx="300" cy="376" rx="220" ry="22" fill="url(#halo)"/>
    <circle cx="300" cy="205" r="207" fill="url(#halo)"/>
    <g stroke="#087fba" strokeWidth=".7" fill="none" opacity=".65">
      <ellipse cx="300" cy="205" rx="229" ry="69" transform="rotate(-23 300 205)"/>
      <ellipse cx="300" cy="205" rx="202" ry="177" transform="rotate(28 300 205)"/>
      <ellipse cx="300" cy="205" rx="166" ry="186" transform="rotate(-24 300 205)"/>
    </g>
    <circle cx="300" cy="205" r="153" stroke="#169cdd" fill="none" opacity=".5"/>
    <circle cx="300" cy="205" r="150" fill="url(#ocean)" stroke="#3dbbe8"/>
    <g clipPath="url(#sphere)">
      <g fill="url(#land)" stroke="#57a0b8" strokeWidth=".6">
        <path d="M165 118l25-30 29-7 16 12 19-9 12 11-6 17 14 12-13 12-24 1-13 20-21 4-13 29-20-7-6-30-16-13zM240 63l34-6 20 13-9 26-19 11-19-13zM205 187l17 6 10 23 20 11 6 19-10 9-21-15-8-19-15-12zM252 246l28 3 28 16 7 29-16 30-11 42-15 9-5-28-15-24 2-24-15-25z"/>
        <path d="M324 101l16-17 22 5 13-13 25 8 24 22 35 7 17 24-19 12-19-3-13 19-28-2-12 14-20-16-20 1-12-19-23 2-8-15 16-8zM330 165l28-7 31 14 15 35-17 22-12 37-21 2-16-24-3-31-18-22zM409 176l22 5 16 24-10 26-14-19zM430 265l29-17 31 14 12 28-28 12-32-10zM318 92l-9-15 7-15 10 9z"/>
      </g>
      <g stroke="#2583b4" strokeWidth=".7" opacity=".45" fill="none">
        {[50,100,140].map(r=><ellipse key={r} cx="300" cy="205" rx={r} ry="150"/>)}
        {[105,155,205,255,305].map(y=><path key={y} d={`M145 ${y} Q300 ${y+35} 455 ${y}`}/>)}
      </g>
      <g fill="#f3c788" opacity=".85">{Array.from({length:65},(_,i)=>{const x=170+(i*43%260), y=90+(i*31%215); return <circle key={i} cx={x} cy={y} r={i%3===0?1.4:.7}/>;})}</g>
      <g stroke="#12bafa" fill="none" opacity=".8"><path d="M197 144Q300 90 415 180L325 233 242 280 197 144 325 233 350 130 415 180"/><path d="M242 280Q370 340 415 180"/></g>
    </g>
    <g fill="#51e8ff" stroke="#15b7ff">{[[197,144],[415,180],[325,233],[242,280],[350,130],[137,239],[466,123],[411,53],[215,61]].map(([x,y],i)=><g key={i}><circle cx={x} cy={y} r="10" opacity=".5" filter="url(#glow)"/><circle cx={x} cy={y} r="4" fill="#bdfaff"/><circle cx={x} cy={y} r="9" fill="none" opacity=".6"/></g>)}</g>
  </svg></div>;
}

export function MetricCards({workflows, loaded}: {workflows:Row[];loaded:boolean}) {
  const active=workflows.filter(w=>w.is_active).length;
  return <div className="summary">
    <div className="metric blue"><div className="metric-label"><span className="metric-icon"><Box size={23}/></span><span>REGISTERED<br/>WORKFLOWS</span></div><strong>{loaded?workflows.length:'—'}</strong><small>In this installation</small><Sparkline/></div>
    <div className="metric green"><div className="metric-label"><span className="metric-icon"><CirclePlay size={23}/></span><span>ACTIVE<br/>WORKFLOWS</span></div><strong>{loaded?active:'—'}</strong><small><i className="status-dot"/>{loaded&&workflows.length?`${Math.round(active/workflows.length*100)}% of registered workflows`:'No activity percentage yet'}</small><Sparkline/></div>
    <div className="metric red"><div className="metric-label"><span className="metric-icon"><Shield size={23}/></span><span>EXECUTION DEFAULT</span></div><strong className="text-small">Deny unless<br/>allowed</strong><small>Explicit policy before execution</small></div>
  </div>;
}

function Sparkline(){return <svg className="metric-wave" viewBox="0 0 180 90" aria-hidden="true"><path d="M0 90 Q25 80 47 83 T87 51 T127 42 T165 7 L180 11V90Z" fill="currentColor" opacity=".1"/><path d="M0 90 Q25 80 47 83 T87 51 T127 42 T165 7 L180 11" fill="none" stroke="currentColor" strokeWidth="1.5"/></svg>}

export function StatusCard({health,latency}:{health:string;latency:number|null}){
  return <section className="panel system-card"><div className="rail-heading">SYSTEM STATUS<Activity size={22}/></div><h3 className={health==='healthy'?'healthy':'muted'}><i className="status-dot"/>{health==='healthy'?'Control plane operational':health==='checking'?'Checking connection…':'Connection unavailable'}</h3><div className="status-row"><Database size={15}/>Database<strong>{health==='healthy'?'Connected':'Unverified'}</strong></div><div className="status-row"><Activity size={15}/>Health check<strong>{latency===null?'—':`${latency} ms`}</strong></div><div className="status-row"><Shield size={15}/>Deployment<strong>Local</strong></div></section>
}

export function RightRail({workflows,runs,loaded,onRuns}:{workflows:Row[];runs:Row[];loaded:boolean;onRuns:()=>void}){
  const counts=['low','medium','high','critical'].map(level=>workflows.filter(w=>String(w.risk_level).toLowerCase()===level).length);
  const total=workflows.length;
  let stop=0;
  const colors=['#00dba0','#ffbc32','#ff553e','#c076ff'];
  const gradient=total?counts.map((count,i)=>{const start=stop;stop+=count/total*100;return `${colors[i]} ${start}% ${stop}%`;}).join(','):'#153149 0% 100%';
  return <div className="rail-content"><div className="layer-art" aria-hidden="true"><div className="layer-stack">{['POLICY','EXECUTION','AUDIT','GOVERNANCE'].map((label,i)=><div className="layer" key={label} style={{top:i*27}}><span>{i===0?'R.A.E.':''}</span><b>{label}</b></div>)}</div><p>AUTOMATE WITH CONFIDENCE</p></div>
    <section className="panel risk-card"><h3>RISK DISTRIBUTION</h3><div className="risk-layout"><div className="donut" style={{background:`conic-gradient(${gradient})`}}><div><strong>{loaded?total:'—'}</strong><span>Workflows</span></div></div><div className="risk-legend">{['Low','Medium','High','Critical'].map((label,i)=><div key={label}><i style={{background:colors[i]}}/>{label}<b>{loaded?counts[i]:'—'}</b></div>)}</div></div></section>
    <section className="panel activity-card"><div className="rail-heading"><h3>RECENT RUNS</h3><button onClick={onRuns}>View all ↗</button></div>{runs.length?runs.slice(0,5).map(run=><div className="activity-row" key={run.id}><CheckCircle2 size={24} className={run.status==='success'?'healthy':'muted'}/><div><strong>{run.status==='success'?'Workflow completed':`Run ${run.status}`}</strong><span>{workflows.find(w=>w.id===run.workflow_id)?.name||run.id.slice(0,8)}</span><time>{new Date(run.started_at).toLocaleString()}</time></div></div>):<p className="rail-empty">{loaded?'Your agent’s runs will appear here.':'Run history unavailable.'}</p>}</section>
  </div>;
}
