"use client";
import { useState } from 'react';
import { History } from 'lucide-react';
import { request, Row } from '@/lib/api';

const date = (value?: string) => value ? new Date(value).toLocaleString() : '—';

export default function RunHistory({rows, workflows, token}: {rows: Row[]; workflows: Row[]; token: string}) {
  const [selected, setSelected] = useState<Row | null>(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const visible = rows.filter(row => !status || row.status === status);
  async function detail(id: string) {
    setBusy(true); setError('');
    try {setSelected(await request<Row>(`orchestrations/runs/${id}`, token));}
    catch(e) {setError((e as Error).message);}
    finally {setBusy(false);}
  }
  return <>
    <section className="panel">
      <div className="panel-title"><h2>Orchestration runs</h2><label>Status <select value={status} onChange={e=>setStatus(e.target.value)}><option value="">All</option>{['pending','success','error','denied'].map(s=><option key={s}>{s}</option>)}</select></label></div>
      <p className="run-note">Latest 100 runs · Includes direct model calls. Pending means no completion has been recorded.</p>
      {error && <p role="alert" className="error">{error}</p>}
      {!visible.length ? <div className="empty"><History size={32}/><h3>No matching runs yet</h3><p>Run an agent workflow to see its steps and governance decisions here.</p></div> : <div className="table-wrap"><table><thead><tr><th>Run / workflow</th><th>Status</th><th>Started</th><th>Completed</th><th>Steps</th><th>Details</th></tr></thead><tbody>{visible.map(row=><tr key={row.id}>
        <td><strong>{row.id.slice(0,8)}</strong><span className="row-sub">{workflows.find(w=>w.id===row.workflow_id)?.name || row.workflow_id}</span><span className="row-sub">{row.source==='chat_completion'?'Direct model call':'Workflow run'}</span></td>
        <td><span className={`badge ${['denied','error'].includes(row.status)?'warning':''}`}>{row.status}</span></td><td>{date(row.started_at)}</td><td>{date(row.completed_at)}</td><td>{row.step_count}</td><td><button disabled={busy} onClick={()=>void detail(row.id)}>View timeline</button></td>
      </tr>)}</tbody></table></div>}
    </section>
    {selected && <section className="panel detail"><div className="panel-title"><h2>Run timeline</h2><button onClick={()=>setSelected(null)}>Close</button></div><div className="run-note"><p>{selected.id}</p><p>Status: <strong>{selected.status}</strong> · Request: {selected.request_id}</p>{selected.decision_reason && <p className="error">{selected.decision_reason}</p>}</div>
      <div className="run-note">{selected.context ? <><p>Tenant: {selected.tenant_id}</p><p>Execution context: {selected.context_id}</p><p>Actor: {selected.actor_id}</p><p>Protected scope: workflow {selected.context.workflow_id}</p></> : <p>Legacy run: context and policy snapshots were not recorded.</p>}</div>
      <ol className="run-timeline">{selected.steps.map((step: Row)=><li key={step.id}><div><strong>{step.step_id}</strong> <span className={`badge ${['denied','error'].includes(step.status)?'warning':''}`}>{step.status}</span></div><p>{step.step_type}{step.model?` · ${step.model}`:''}</p><p>{date(step.started_at)} → {date(step.completed_at)}</p>{step.decision_reason && <p className="error">{step.decision_reason}</p>}{Object.keys(step.token_usage).length>0 && <p>Tokens: {Object.entries(step.token_usage).map(([key,value])=>`${key}: ${value}`).join(' · ')}</p>}</li>)}</ol>
      {selected.policy_snapshots?.map((snapshot: Row)=><details key={snapshot.id} className="run-note"><summary>Policy snapshot {snapshot.id.slice(0,8)} · {date(snapshot.created_at)}</summary><p>Recorded decision inputs · SHA-256 {snapshot.content_hash}</p><pre>{JSON.stringify(snapshot.content,null,2)}</pre></details>)}
      {selected.events?.length>0 && <details className="run-note"><summary>Execution events ({selected.events.length})</summary><ol>{selected.events.map((event: Row)=><li key={event.id}>{event.event_type} · {event.step_id||'run'} · {event.state}</li>)}</ol></details>}
      <p className="run-note">History stores execution metadata. Email content, prompts, and model responses are not retained here.</p>
    </section>}
  </>;
}
