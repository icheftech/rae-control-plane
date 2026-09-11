"use client";
import { useEffect, useRef, useState, FormEvent } from 'react';
import { request, Row } from '@/lib/api';

export default function LocalJobs({token, workflows, canSubmit, onRun}: {
  token:string; workflows:Row[]; canSubmit:boolean; onRun:(id:string)=>void;
}) {
  const [jobs,setJobs]=useState<Row[]>([]);
  const [workers,setWorkers]=useState<Row[]>([]);
  const [loaded,setLoaded]=useState(false);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [workflow,setWorkflow]=useState('');
  const [task,setTask]=useState('');
  const [notice,setNotice]=useState('');
  const submission=useRef<{body:string;key:string}|null>(null);
  useEffect(()=>{
    let active=true;
    let timer:ReturnType<typeof setTimeout>;
    async function refresh(){
      try{
        const [nextJobs,nextWorkers]=await Promise.all([request<Row[]>('local-jobs',token),request<Row[]>('local-jobs/workers',token)]);
        if(active){setJobs(nextJobs);setWorkers(nextWorkers);setLoaded(true);setError('');}
      }catch(e){if(active){setError((e as Error).message);setLoaded(false);}}
      if(active)timer=setTimeout(refresh,5000);
    }
    void refresh();
    return ()=>{active=false;clearTimeout(timer);};
  },[token]);
  async function submit(e:FormEvent){
    e.preventDefault();setBusy(true);setNotice('');
    const body=JSON.stringify({workflow_id:workflow,task_key:task});
    if(submission.current?.body!==body)submission.current={body,key:crypto.randomUUID()};
    try{
      const job=await request<Row>('local-jobs',token,'POST',{workflow_id:workflow,task_key:task,idempotency_key:submission.current.key});
      setJobs(current=>[job,...current.filter(j=>j.id!==job.id)]);
      setNotice(`Job ${job.id.slice(0,8)} queued. The worker will pick it up when connected.`);
      submission.current=null;
    }catch(e){setNotice((e as Error).message);}
    finally{setBusy(false);}
  }
  return <section className="panel">
    <div className="panel-title"><h2>Local worker jobs</h2><span>{!loaded?'Connection unknown':workers.some(w=>w.connected)?'Worker connected':'Worker offline'}</span></div>
    <p className="run-note">Jobs persist across restarts. Interrupted jobs are never automatically replayed. Status refreshes every five seconds.</p>
    {canSubmit&&<form className="edit-form" onSubmit={submit}>
      <label>Workflow<select required value={workflow} onChange={e=>setWorkflow(e.target.value)}><option value="">Select workflow</option>{workflows.filter(w=>w.is_active).map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select></label>
      <label>Installed task key<input required pattern="[a-zA-Z0-9_-]{1,80}" value={task} onChange={e=>setTask(e.target.value)} placeholder="local-worker-demo"/></label>
      <p className="small">Task definitions must first be installed on this machine.</p><button className="primary" disabled={busy}>Queue local job</button>
    </form>}
    {notice&&<p role="status" className="run-note">{notice}</p>}
    {error&&<p role="alert" className="error run-note">{error}</p>}
    {loaded&&!jobs.length?<p className="run-note">No local jobs yet.</p>:<div className="table-wrap"><table><thead><tr><th>Job / task</th><th>Status</th><th>Created</th><th>Outcome</th></tr></thead><tbody>{jobs.map(job=><tr key={job.id}>
      <td><strong>{job.task_key}</strong><span className="row-sub">{job.id.slice(0,8)}</span></td>
      <td><span className={`badge ${['interrupted','error','denied'].includes(job.status)?'warning':''}`}>{job.status}</span></td>
      <td>{new Date(job.created_at).toLocaleString()}</td>
      <td>{job.reason&&<span className="row-sub">{job.reason}</span>}{job.run_id&&<button onClick={()=>onRun(job.run_id)}>View run evidence</button>}</td>
    </tr>)}</tbody></table></div>}
  </section>;
}
