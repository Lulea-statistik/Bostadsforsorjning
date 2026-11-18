'use strict';
(() => {
  const body=document.getElementById('indicators');
  const detail=document.getElementById('rent-detail');
  if(!body||!detail)return;
  const fmt=new Intl.NumberFormat('sv-SE',{maximumFractionDigits:1});
  const unit=document.getElementById('rent-unit');
  const from=document.getElementById('rent-start-year');
  const status=document.getElementById('rent-status');
  const svg=document.getElementById('rent-chart');
  const table=document.getElementById('rent-rows');
  const ns='http://www.w3.org/2000/svg';
  let data=[],opener=null;
  const name='Medel- och medianhyra';
  const color={mean:'#316c80',median:'#b63d51'};
  function node(tag,attrs={},text){
    const e=document.createElementNS(ns,tag);
    Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,String(v)));
    if(text!==undefined)e.textContent=text;
    return e;
  }
  const value=(r,key)=>r[unit.value]?.[key];
  const present=v=>Number.isFinite(v)?fmt.format(v):'Saknas';
  function decorate(){
    for(const row of body.rows){
      if(row.cells[0]?.textContent.trim()!==name)continue;
      if(!row.dataset.indicatorDetail){
        row.dataset.indicatorDetail='rent';
        const b=document.createElement('button');
        b.className='indicator-open';b.type='button';b.textContent=name;
        b.setAttribute('aria-controls','rent-detail');
        row.cells[0].replaceChildren(b);
      }
      const last=[...data].reverse().find(r=>Number.isFinite(r.annual.mean));
      if(last)row.cells[2].textContent=present(last.annual.mean)+' kr/m²/år ('+last.year+')';
      row.querySelector('button')?.setAttribute('aria-expanded',String(!detail.hidden));
    }
  }
  function toggle(){
    if(detail.hidden){
      document.getElementById('population-detail').hidden=true;
      document.getElementById('housing-detail').hidden=true;
      detail.hidden=false;
      detail.scrollIntoView({behavior:'smooth',block:'nearest'});
    }else detail.hidden=true;
    decorate();
  }
  body.addEventListener('click',event=>{
    const row=event.target.closest('tr[data-indicator-detail="rent"]');
    if(!row)return;
    opener=row.querySelector('button');toggle();
  });
  document.getElementById('rent-close').addEventListener('click',()=>{
    detail.hidden=true;decorate();if(opener?.isConnected)opener.focus();
  });
  function chart(){
    const selected=data.filter(r=>r.year>=Number(from.value));
    svg.replaceChildren();
    if(selected.length===0)return;
    const W=900,H=340,L=76,R=24,T=25,B=57;
    const vals=selected.flatMap(r=>['mean','median'].map(k=>value(r,k))).filter(Number.isFinite);
    if(!vals.length)return;
    const min=0,max=Math.max(10,Math.ceil(Math.max(...vals)/100)*100);
    const x=i=>L+(selected.length===1?(W-L-R)/2:i*(W-L-R)/(selected.length-1));
    const y=v=>H-B-(v-min)/(max-min)*(H-B-T);
    for(let i=0;i<=4;i++){
      const v=max*i/4;
      const yy=y(v);
      svg.append(node('line',{x1:L,x2:W-R,y1:yy,y2:yy,stroke:'#d7dee6','stroke-dasharray':i?'3 5':'none'}));
      svg.append(node('text',{x:L-9,y:yy+4,'text-anchor':'end'},present(v)));
    }
    selected.forEach((r,i)=>{
      svg.append(node('text',{x:x(i),y:H-20,'text-anchor':'middle'},String(r.year)));
    });
    for(const key of ['mean','median']){
      let points=[];
      function flush(){
        if(points.length>1)svg.append(node('polyline',{points:points.join(' '),fill:'none',stroke:color[key],'stroke-width':3,'stroke-linejoin':'round','stroke-linecap':'round'}));
        points=[];
      }
      selected.forEach((r,i)=>{
        const v=value(r,key);
        if(!Number.isFinite(v)){flush();return}
        points.push(x(i)+','+y(v));
        const c=node('circle',{cx:x(i),cy:y(v),r:4,fill:color[key]});
        const margin=value(r,key+'_margin');
        c.append(node('title',{},r.year+': '+(key==='mean'?'Medelhyra':'Medianhyra')+' '+present(v)+' '+(unit.value==='annual'?'kr/m²/år':'kr/m²/mån')+(Number.isFinite(margin)?' (± '+present(margin)+')':'')));
        svg.append(c);
      });
      flush();
    }
    svg.prepend(node('title',{},'Luleå: medelhyra och medianhyra '+selected[0].year+'–'+selected.at(-1).year));
  }
  function render(){
    const latest=[...data].reverse().find(r=>Number.isFinite(value(r,'mean')));
    const unitText=unit.value==='annual'?'kr/m²/år':'kr/m²/månad';
    status.textContent=latest?'Senaste medelhyra: '+present(value(latest,'mean'))+' '+unitText+' ('+latest.year+'). Medianhyra: '+present(value(latest,'median'))+' '+unitText+'.':'Inga publicerade hyresvärden för valt mått.';
    document.getElementById('rent-note').textContent=unit.value==='annual'
      ?'Årshyra för hela kalenderåret; publicerade felmarginaler visas i tabell och vid punkter.'
      :'Ny månadshyra efter årlig hyresändring; det är ett separat SCB-mått. Publicerade felmarginaler visas i tabell och vid punkter.';
    table.replaceChildren();
    [...data].reverse().forEach(r=>{
      const tr=document.createElement('tr');
      ['year','mean','mean_margin','median','median_margin'].forEach(key=>{
        const td=document.createElement('td');td.textContent=key==='year'?String(r.year):present(value(r,key));tr.append(td);
      });
      table.append(tr);
    });
    svg.setAttribute('aria-label','Medelhyra och medianhyra i Luleå, '+unitText);
    chart();
  }
  new MutationObserver(decorate).observe(body,{childList:true});
  decorate();
  async function load(){
    try{
      const response=await fetch('data/rent.json',{cache:'no-cache'});
      if(!response.ok)throw Error('SCB:s hyresdata är ännu inte importerade');
      const json=await response.json();
      if(json.municipality!=='2580'||!Array.isArray(json.data)||!json.data.length)throw Error('Fel dataformat eller kommun');
      if(json.data.some((r,i)=>!Number.isInteger(r.year)||i&&r.year<=json.data[i-1].year||['annual','new_monthly'].some(k=>!r[k]||['mean','median','mean_margin','median_margin'].some(m=>r[k][m]!==null&&!Number.isFinite(r[k][m])))))throw Error('Ogiltig eller osorterad hyresstatistik');
      data=json.data;
      data.forEach(r=>{const opt=document.createElement('option');opt.value=String(r.year);opt.textContent=String(r.year);from.append(opt)});
      from.value=String(data[0].year);
      unit.addEventListener('change',render);
      from.addEventListener('change',render);
      document.getElementById('rent-data-area').hidden=false;
      render();
      decorate();
    }catch(e){status.textContent='Hyresstatistik kan ännu inte visas: '+e.message+'. Inga obekräftade värden visas.'}
  }
  load();
})();
