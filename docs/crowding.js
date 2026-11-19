'use strict';
// Data comes from docs/data/content.json, indicator 8. Only source-confirmed years are plotted.
(function(){
 const el=id=>document.getElementById(id), ns='http://www.w3.org/2000/svg';
 function svgNode(tag,attrs,text){const n=document.createElementNS(ns,tag);Object.entries(attrs||{}).forEach(([k,v])=>n.setAttribute(k,String(v)));if(text!==undefined)n.textContent=text;return n}
 function draw(series){
  const svg=el('crowding-chart');svg.replaceChildren();
  const data=series.filter(d=>Number.isInteger(d.year)&&Number.isFinite(d.percent)).sort((a,b)=>a.year-b.year);
  if(!data.length)return;
  const W=900,H=350,L=62,R=28,T=38,B=55, iw=W-L-R, ih=H-T-B;
  const lo=Math.min(...data.map(d=>d.year)),hi=Math.max(...data.map(d=>d.year));
  const ymin=0,ymax=Math.max(10,Math.ceil((Math.max(...data.map(d=>d.percent))+1)/2)*2);
  const x=year=>lo===hi?L+iw/2:L+(year-lo)/(hi-lo)*iw;
  const y=p=>T+ih-(p-ymin)/(ymax-ymin)*ih;
  const label=(x0,y0,t,attr={})=>svg.append(svgNode('text',{x:x0,y:y0,'text-anchor':'middle',fill:'#32404a','font-size':15,...attr},t));
  for(let v=0;v<=ymax;v+=2){const yy=y(v);svg.append(svgNode('line',{x1:L,y1:yy,x2:W-R,y2:yy,stroke:'#d9dfe2','stroke-dasharray':'6 4'}));label(L-20,yy+5,v.toLocaleString('sv-SE',{minimumFractionDigits:1})+'',{ 'text-anchor':'end','font-size':13})}
  svg.append(svgNode('line',{x1:L,y1:T+ih,x2:W-R,y2:T+ih,stroke:'#6b7280'}));
  if(data.length>1){const parts=[];data.forEach((d,i)=>parts.push((i===0?'M':'L')+x(d.year)+' '+y(d.percent)));
   svg.append(svgNode('path',{d:parts.join(' '),stroke:'#4c9b69','stroke-width':3,fill:'none','stroke-linejoin':'round'}))}
  for(const d of data){const xx=x(d.year),yy=y(d.percent);svg.append(svgNode('circle',{cx:xx,cy:yy,r:5.2,fill:'#4c9b69'}));label(xx,yy-14,d.percent.toLocaleString('sv-SE',{minimumFractionDigits:1}),{'font-size':16});label(xx,T+ih+28,String(d.year),{'font-size':14})}
 }
 window.openCrowdingDetail=function(indicator){
  const section=el('crowding-detail');if(!section)return;
  document.querySelectorAll('.indicator-detail').forEach(e=>{e.hidden=true});
  section.hidden=false;draw(indicator.crowdingSeries||[]);
  const n=(indicator.crowdingSeries||[]).length;
  el('crowding-status').textContent=n<2?'Endast 2024 har verifierats för detta mått. En linje visas först när minst två årsvärden finns; den bifogade Boverkets graf avser ett annat hushållsurval.':'';
  section.scrollIntoView({behavior:'smooth',block:'start'});
 };
 el('crowding-close')?.addEventListener('click',()=>{el('crowding-detail').hidden=true});
})();
