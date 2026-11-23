'use strict';
// Data comes from docs/data/content.json, indicator 8. Only source-confirmed years are plotted.
(function(){
 const el=id=>document.getElementById(id), ns='http://www.w3.org/2000/svg';
 const formatOneDecimal=value=>Number(value).toLocaleString('sv-SE',{minimumFractionDigits:1,maximumFractionDigits:1});
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
  for(let v=0;v<=ymax;v+=2){const yy=y(v);svg.append(svgNode('line',{x1:L,y1:yy,x2:W-R,y2:yy,stroke:'#d9dfe2','stroke-dasharray':'6 4'}));label(L-20,yy+5,formatOneDecimal(v),{ 'text-anchor':'end','font-size':13})}
  svg.append(svgNode('line',{x1:L,y1:T+ih,x2:W-R,y2:T+ih,stroke:'#6b7280'}));
  if(data.length>1){const parts=[];data.forEach((d,i)=>parts.push((i===0?'M':'L')+x(d.year)+' '+y(d.percent)));
   svg.append(svgNode('path',{d:parts.join(' '),stroke:'#4c9b69','stroke-width':3,fill:'none','stroke-linejoin':'round'}))}
  for(const d of data){const xx=x(d.year),yy=y(d.percent);svg.append(svgNode('circle',{cx:xx,cy:yy,r:5.2,fill:'#4c9b69'}));label(xx,T+ih+28,String(d.year),{'font-size':14})}
 }
 const tbody=el('indicators'),detail=el('crowding-detail'),close=el('crowding-close');
 if(!tbody||!detail||!close)return;
 let opener=null;
 const indicatorName='Trångboddhet bland hushåll som hyr lägenhet i flerbostadshus';
 function decorate(){
   for(const row of tbody.rows){
     // Re-create the exact same button type as rent-pilot.js even after search/filter redraws.
     if(row.cells[0]?.textContent.trim()!==indicatorName)continue;
     row.dataset.indicatorDetail='crowding';
     let button=row.cells[0].querySelector('button.indicator-open');
     if(!button){
       button=document.createElement('button');
       button.type='button';
       button.className='indicator-open';
       button.textContent=indicatorName;
       row.cells[0].replaceChildren(button);
     }
     button.setAttribute('aria-controls','crowding-detail');
     button.setAttribute('aria-expanded',String(!detail.hidden));
   }
 }
 function toggle(){
   if(detail.hidden){
     document.querySelectorAll('.indicator-detail').forEach(other=>{if(other!==detail)other.hidden=true});
     detail.hidden=false;
     const selected=window.crowdingObservations||[];
     draw(selected);
     el('crowding-status').textContent=selected.length<2
       ? 'Endast ett årsvärde finns för det valda måttet. En linje visas när minst två år finns.'
       : '';
     detail.scrollIntoView({behavior:'smooth',block:'nearest'});
   }else detail.hidden=true;
   decorate();
 }
 // Use the same interactive button styling, click delegation and focus handling
 // as the population, housing and rent indicators.
 tbody.addEventListener('click',event=>{
   const row=event.target.closest('tr[data-indicator-detail="crowding"]');
   if(!row)return;
   opener=row.querySelector('.indicator-open');
   toggle();
 });
 close.addEventListener('click',()=>{
   detail.hidden=true;
   decorate();
   if(opener?.isConnected)opener.focus();
 });
 new MutationObserver(decorate).observe(tbody,{childList:true});
 decorate();
 // The table is populated asynchronously from content.json by app.js.
 fetch('data/content.json').then(r=>{if(!r.ok)throw Error('Data kunde inte läsas');return r.json()})
  .then(json=>{
    const indicator=json.indicators?.find(r=>r.id===8);
    window.crowdingObservations=indicator?.crowdingSeries||[];
  })
  .catch(()=>{el('crowding-status').textContent='Trångboddhetsserien kunde inte läsas.'});
})();
