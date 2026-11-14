import React, { useEffect, useState } from 'react';
import { MessageSquare, Library, ChartNoAxesCombined, PanelLeftClose, PanelLeftOpen, FileText, ArrowUpRight, Upload, Plus, RefreshCw } from 'lucide-react';
import './WorkspacePages.css';
import { usageValue, spendingCoverage } from './usageView.js';
import { workspaceRequest } from './workspaceRequest.js';
const labels = {chats:'Chats',dataset:'Dataset',spending:'Spending'};
const icons = {chats:MessageSquare,dataset:Library,spending:ChartNoAxesCombined};
export function WorkspaceNavigation({route,onNavigate,collapsed,onCollapse,chatWorkspace}) {
 const [drawerOpen,setDrawerOpen]=useState(false);
 const expanded=!collapsed||drawerOpen;
 const go=id=>{setDrawerOpen(false);onNavigate(id)};
 const threadName=thread=>thread.title===thread.document_name?thread.title.replace(/^[a-f0-9]{12}-/i,''):thread.title;
 return <nav className={`workspace-nav ${collapsed?'is-collapsed':''} ${drawerOpen?'mobile-expanded':''}`} aria-label="Main navigation">
   <button className="mobile-nav-toggle" aria-label={drawerOpen?'Close navigation':'Open navigation'} onClick={()=>setDrawerOpen(value=>!value)}>{drawerOpen?<PanelLeftClose size={18}/>:<PanelLeftOpen size={18}/>}</button>
   <div className="nav-brand"><span className="metria-monogram">m</span>{expanded&&<strong>Metria</strong>}<button className="nav-collapse" aria-label={collapsed?'Expand navigation':'Collapse navigation'} onClick={onCollapse}>{collapsed?<PanelLeftOpen size={18}/>:<PanelLeftClose size={18}/>}</button></div>
   <div className="nav-primary">
     <div className="nav-chat-row"><button className="nav-link" aria-current={route==='chats'?'page':undefined} title="Chats" onClick={()=>go('chats')}><MessageSquare size={21} strokeWidth={1.7}/>{expanded&&<span>Chats</span>}</button>{expanded&&<button className="nav-add-chat" aria-label="New chat" title="New chat" onClick={()=>{go('chats');chatWorkspace.create(null)}}><Plus size={17}/></button>}</div>
     {expanded&&<div className="nav-chat-threads" aria-label="Chat threads">{chatWorkspace.threads.map(thread=><button key={thread.id} className={`nested-chat ${route==='chats'&&thread.id===chatWorkspace.active?'is-active':''}`} onClick={()=>{go('chats');chatWorkspace.choose(thread.id)}} title={threadName(thread)}>{threadName(thread)}</button>)}{chatWorkspace.historyUnavailable&&chatWorkspace.threads.length===0&&<button className="nested-chat" onClick={chatWorkspace.reconnect}>Reconnect history</button>}</div>}
     <div className="nav-other-pages">{['dataset','spending'].map(id=>{const Icon=icons[id];return <button className="nav-link" key={id} aria-current={route===id?'page':undefined} title={labels[id]} onClick={()=>go(id)}><Icon size={21} strokeWidth={1.7}/>{expanded&&<span>{labels[id]}</span>}</button>})}</div>
   </div>
   <div className="nav-footer"><span className="workspace-avatar">M</span>{expanded&&<div><strong>Junction workspace</strong><small>Blueprint intelligence</small></div>}</div>
 </nav>;
}
function useResource(url) {
 const [state,setState]=useState({data:null,error:'',loading:true});
 useEffect(()=>{const controller=new AbortController();setState({data:null,error:'',loading:true});workspaceRequest(url,'GET',undefined,{signal:controller.signal}).then(data=>{if(!controller.signal.aborted)setState({data,error:'',loading:false})}).catch(error=>{if(!controller.signal.aborted)setState({data:null,error:error.message,loading:false})});return()=>controller.abort()},[url]);return state;
}
export function DatasetPage({onOpen}) {
 const [search,setSearch]=useState(''),[term,setTerm]=useState(''),[source,setSource]=useState(''),[offset,setOffset]=useState(0);
 useEffect(()=>{const t=setTimeout(()=>{setTerm(search);setOffset(0)},200);return()=>clearTimeout(t)},[search]);
 const params=new URLSearchParams({uploaded:'false',limit:'24',offset:String(offset),search:term,...(source?{source}:{})});
 const {data,error,loading}=useResource(`/api/documents?${params}`);
 return <section className="workspace-page"><div className="page-heading"><div><span className="page-breadcrumb">Workspace / Dataset</span><h1>Drawing library</h1><p>Explore the plans and models provided for the challenge.</p></div><span className="page-count">{data?.total?.toLocaleString()??'—'} drawings</span></div><div className="page-filters"><input aria-label="Search dataset" placeholder="Search plans, buildings or filenames…" value={search} onChange={e=>setSearch(e.target.value)}/><select aria-label="Dataset collection" value={source} onChange={e=>{setSource(e.target.value);setOffset(0)}}><option value="">All collections</option>{(data?.sources||[]).filter(s=>s.source!=='uploads').map(s=><option key={s.source} value={s.source}>{s.source.replaceAll('_',' ')} · {s.count}</option>)}</select></div>{error&&<p role="alert">{error}</p>}{loading&&<p role="status">Loading drawings…</p>}<div className="dataset-grid">{(data?.documents||[]).map(doc=><button className="dataset-document" key={doc.id} onClick={()=>onOpen(doc.id)}><div className="document-preview">{doc.format!=='dwg'&&<img src={`/api/documents/${encodeURIComponent(doc.id)}/pages/1/image?size=400`} alt="" loading="lazy" onError={e=>{e.currentTarget.style.display='none'}}/>}<FileText size={36} strokeWidth={1}/><span>{doc.format.toUpperCase()}</span></div><strong>{doc.name}</strong><small>{doc.source.replaceAll('_',' ')}</small><span className="document-open">Open in Chats <ArrowUpRight size={14}/></span></button>)}</div>{!loading&&!error&&data?.total===0&&<div className="page-empty"><Library size={32}/><h2>No drawings found</h2><p>Try another name or collection. The dataset is loaded separately from your uploads.</p></div>}<div className="page-pagination"><button disabled={offset===0||loading} onClick={()=>setOffset(Math.max(0,offset-24))}>Previous</button><span>{data?.total?`${offset+1}–${Math.min(offset+24,data.total)} of ${data.total}`:'0 drawings'}</span><button disabled={!data||offset+24>=data.total||loading} onClick={()=>setOffset(offset+24)}>Next</button></div></section>;
}
const colors=['#45975f','#f2c779','#4b82d1','#9276b9','#d78769'];
const integer=n=>Number(n||0).toLocaleString();
const price=n=>n==null?'Unavailable':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:4}).format(n);
export function SpendingPage() {
 const [days,setDays]=useState(30),[metric,setMetric]=useState('tokens'),[refresh,setRefresh]=useState(0);
 const {data,error,loading}=useResource(`/api/usage/overview?days=${days}&refresh=${refresh}`);
 const usage=data?.aggregate,models=usage?.models||[],daily=data?.daily||[];
 const {requests,unpriced,priced,knownCost}=spendingCoverage(usage);
 const maximum=Math.max(metric==='cost'?0.0001:1,...daily.map(day=>usageValue(day.usage,metric)));
 const dateLabel=date=>date?new Date(date+'T00:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',timeZone:'UTC'}):'';
 const compact=value=>new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:1}).format(value);
 const metricLabel={tokens:'tokens',calls:'requests',cost:'USD'}[metric];
 return <section className="workspace-page spending-page">
   <div className="page-heading"><div><h1>Spending</h1><p>Usage across all chats.</p></div>
     <div className="period-controls"><select aria-label="Usage period" value={days} onChange={event=>setDays(Number(event.target.value))}><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option></select><button aria-label="Refresh usage" disabled={loading} onClick={()=>setRefresh(value=>value+1)}><RefreshCw size={16}/></button></div>
   </div>
   {error&&<div className="usage-error" role="alert"><p>{error}</p><button onClick={()=>setRefresh(value=>value+1)}>Try again</button></div>}
   {loading&&<p role="status">Loading recorded usage…</p>}
   {data&&<>
     <div className="usage-stats">
       <div><span>Tracked cost</span><strong>{priced||!requests?price(knownCost):'No rates set'}</strong><small>{unpriced?`${priced} of ${requests} requests priced`:'Based on recorded token usage'}</small></div>
       <div><span>Requests</span><strong>{integer(requests)}</strong><small>{days===1?'Today':`Over the last ${days} days`}</small></div>
       <div><span>Recorded tokens</span><strong>{integer(usageValue(usage,'tokens'))}</strong><small>{integer(usage.input_tokens)} input · {integer(usage.output_tokens)} output</small></div>
     </div>
     <div className="usage-chart-card"><div className="chart-heading"><div><h2>Daily usage</h2><p>{metric==='cost'&&unpriced?'Cost for priced requests only':'Grouped by model'} · UTC</p></div><select aria-label="Usage chart metric" value={metric} onChange={event=>setMetric(event.target.value)}><option value="tokens">Tokens</option><option value="calls">Requests</option><option value="cost">Tracked cost</option></select></div>
       {!requests?<div className="chart-empty">No model requests in this period.</div>:metric==='cost'&&!priced?<div className="chart-empty">Configure a model rate to track costs for these requests.</div>:<div className="metria-plot" role="img" aria-label={`Daily ${metricLabel} by model`}>
         <div className="metria-plot-axis"><span>{metric==='cost'?price(maximum):compact(maximum)}</span><span>{metric==='cost'?price(maximum/2):compact(maximum/2)}</span><span>0</span></div>
         <div className="metria-bars">{daily.map(day=><div key={day.date} className="metria-bar-column" title={dateLabel(day.date)}>{models.map((model,index)=>{const value=usageValue(day.usage.model_usage?.find(group=>group.model===model),metric);return <div key={model} style={{height:`${value/maximum*100}%`,background:colors[index%colors.length]}} title={`${dateLabel(day.date)} · ${model}: ${metric==='cost'?price(value):integer(value)} ${metricLabel}`}/>})}</div>)}</div>
         <div className="metria-plot-dates"><span>{dateLabel(daily[0]?.date)}</span><span>{dateLabel(daily[Math.floor(daily.length/2)]?.date)}</span><span>{dateLabel(daily.at(-1)?.date)}</span></div>
       </div>}
       <div className="chart-legend">{models.map((model,index)=><span key={model}><i style={{background:colors[index%colors.length]}}/>{model}</span>)}</div>
     </div>
     {requests>0&&<div className="usage-table-wrap"><h2>By model</h2><table className="usage-table"><thead><tr><th>Model</th><th>Requests</th><th>Input tokens</th><th>Output tokens</th><th>Tracked cost</th></tr></thead><tbody>{(usage.model_usage||[]).map(group=><tr key={group.model}><td>{group.model}</td><td>{integer(group.model_calls)}</td><td>{integer(group.input_tokens)}</td><td>{integer(group.output_tokens)}</td><td>{group.unknown_usage_calls===group.model_calls?'Usage not recorded':group.cost_unavailable_calls===group.model_calls?'Rate not configured':price(group.cost_known_usd)}</td></tr>)}</tbody></table></div>}
     <p className="usage-note">{usage.unknown_usage_calls>0&&`${usage.unknown_usage_calls} earlier requests have no token details and are excluded from tracked cost. `}{unpriced>usage.unknown_usage_calls&&`${unpriced-usage.unknown_usage_calls} requests have no configured price and are excluded from tracked cost. `}Costs are token estimates before credits. Native analysis and cached answers use no new model requests.</p>
   </>}
 </section>;
}
