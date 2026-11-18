'use strict';
(() => {
  const tbody = document.getElementById('indicators');
  const detail = document.getElementById('housing-detail');
  if (!tbody || !detail) return;
  const close = document.getElementById('housing-close');
  const status = document.getElementById('housing-status');
  const chart = document.getElementById('housing-chart');
  const yearSelect = document.getElementById('housing-start-year');
  const format = new Intl.NumberFormat('sv-SE');
  const colors = { started: '#316c80', completed: '#b63d51' };
  let rows = [];
  let opener = null;
  const indicatorName = 'Bostadsbyggande – påbörjade och färdigställda';
  const svgNS = 'http://www.w3.org/2000/svg';

  function svgEl(tag, attrs = {}, text) {
    const item = document.createElementNS(svgNS, tag);
    for (const [name, value] of Object.entries(attrs)) item.setAttribute(name, String(value));
    if (text !== undefined) item.textContent = text;
    return item;
  }
  function label(row) {
    return row.partial ? row.year + ' (hittills i år, K1–K' + row.through_quarter + ')' : String(row.year);
  }
  function latestText() {
    const last = rows.at(-1);
    if (!last) return 'Ej inläst';
    return 'Påbörjade ' + format.format(last.started) + ' / färdigställda ' + format.format(last.completed)
      + ' (' + last.year + (last.partial ? ', K1–K' + last.through_quarter + ', hittills' : '') + ')';
  }
  function decorate() {
    for (const row of tbody.rows) {
      if (row.cells[0]?.textContent.trim() !== indicatorName) continue;
      if (!row.dataset.indicatorDetail) {
        row.dataset.indicatorDetail = 'housing';
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'indicator-open';
        button.textContent = indicatorName;
        button.setAttribute('aria-controls', 'housing-detail');
        row.cells[0].replaceChildren(button);
      }
      if (rows.length) row.cells[2].textContent = latestText();
      row.querySelector('.indicator-open')?.setAttribute('aria-expanded', String(!detail.hidden));
    }
  }
  function draw() {
    const visible = rows.filter(r => r.year >= Number(yearSelect.value));
    chart.replaceChildren();
    if (visible.length === 0) return;
    const W=900,H=340,left=70,right=30,top=30,bottom=55;
    const maxValue = Math.max(100, ...visible.flatMap(r => [r.started,r.completed]));
    const bound = Math.ceil(maxValue/100)*100;
    const x = i => left + (visible.length===1 ? (W-left-right)/2 : i*(W-left-right)/(visible.length-1));
    const y = value => H-bottom-value/bound*(H-top-bottom);
    const tick = bound/4;
    for(let i=0;i<=4;i++){
      const value = i*tick;
      const yy=y(value);
      chart.append(svgEl('line',{x1:left,y1:yy,x2:W-right,y2:yy,stroke:'#d7dee6','stroke-dasharray':i===0?'none':'3 5'}));
      chart.append(svgEl('text',{x:left-10,y:yy+4,'text-anchor':'end'},format.format(Math.round(value))));
    }
    const every = Math.max(1,Math.ceil(visible.length/10));
    visible.forEach((item,i) => {
      if(i%every===0 || i===visible.length-1) {
        chart.append(svgEl('text',{x:x(i),y:H-19,'text-anchor':'middle'},String(item.year)+(item.partial?'*':'')));
      }
    });
    for(const metric of ['started','completed']){
      let solid = [];
      visible.forEach((r,i)=>{
        if(r.partial)return;
        solid.push(x(i)+','+y(r[metric]));
      });
      // Complete years only: do not present incomplete year as a full-year line.
      if(solid.length > 1)chart.append(svgEl('polyline',{points:solid.join(' '),fill:'none',stroke:colors[metric],'stroke-width':3,'stroke-linejoin':'round','stroke-linecap':'round'}));
      const last = visible.at(-1);
      if(last.partial && visible.length>1){
        const previous=visible.at(-2);
        chart.append(svgEl('line',{x1:x(visible.length-2),y1:y(previous[metric]),x2:x(visible.length-1),y2:y(last[metric]),stroke:colors[metric],'stroke-width':2.5,'stroke-dasharray':'6 6'}));
      }
      visible.forEach((r,i)=>{
        const marker=svgEl('circle',{cx:x(i),cy:y(r[metric]),r:r.partial?6:3.5,fill:r.partial?'white':colors[metric],stroke:colors[metric],'stroke-width':r.partial?3:1});
        marker.append(svgEl('title',{},label(r)+': '+format.format(r[metric])+' '+(metric==='started'?'påbörjade':'färdigställda')+' lägenheter'));
        chart.append(marker);
      });
    }
    chart.prepend(svgEl('title',{},'Påbörjade och färdigställda lägenheter per år i Luleå. Streckad sista sträcka och ring markerar ofullständigt sista år.'));
  }
  function updateVisibility() {
    tbody.querySelectorAll('[data-indicator-detail="housing"] .indicator-open')
      .forEach(button => button.setAttribute('aria-expanded',String(!detail.hidden)));
  }
  tbody.addEventListener('click',event=>{
    const tr=event.target.closest('tr[data-indicator-detail="housing"]');
    if(!tr)return;
    const button=tr.querySelector('.indicator-open');
    if(detail.hidden){
      opener=button;
      // Keep one expanded detail in the key-metrics view.
      const other=document.getElementById('population-detail');
      if(other) other.hidden=true;
      detail.hidden=false;
      updateVisibility();
      detail.scrollIntoView({behavior:'smooth',block:'nearest'});
    }else{
      detail.hidden=true;
      updateVisibility();
    }
  });
  close.addEventListener('click',()=>{
    detail.hidden=true;
    updateVisibility();
    if(opener?.isConnected)opener.focus();
  });
  new MutationObserver(decorate).observe(tbody,{childList:true});
  decorate();

  async function init(){
    try{
      const response=await fetch('data/housing_construction.json',{cache:'no-cache'});
      if(!response.ok)throw Error('SCB-data har ännu inte importerats');
      const json=await response.json();
      if(json.municipality!=='2580' || !Array.isArray(json.data))throw Error('Fel dataformat eller kommun');
      const values=json.data;
      if(!values.length || values.some((r,i)=>!Number.isInteger(r.year)||!Number.isInteger(r.started)||!Number.isInteger(r.completed) || r.started<0 || r.completed<0 || !Number.isInteger(r.through_quarter) || r.through_quarter<1 || r.through_quarter>4 || r.partial!==(r.through_quarter!==4) || (i>0 && r.year<=values[i-1].year) || (r.partial&&i!==values.length-1)))throw Error('Ogiltig årstidsserie');
      rows=values;
      const latest=rows.at(-1);
      status.textContent='Senaste period: '+label(latest)+'. Påbörjade: '+format.format(latest.started)+'; färdigställda: '+format.format(latest.completed)+' lägenheter.';
      const note=document.getElementById('housing-partial-note');
      note.textContent=latest.partial
        ? '* '+latest.year+' omfattar bara K1–K'+latest.through_quarter+' (hittills i år), inte ett helår. Sista punkten och linjesträckan är särskilt markerade och ska inte jämföras rakt av med föregående helår.'
        : 'Samtliga år är fullständiga kalenderår (K1–K4).';
      const starts=[rows[0].year,2010,2015,2020,2025].filter((y,i,all)=>y<=latest.year && all.indexOf(y)===i && y>=rows[0].year);
      starts.forEach(year=>{const option=document.createElement('option');option.value=String(year);option.textContent=String(year);yearSelect.append(option)});
      yearSelect.value=String(starts.find(x=>x===2010)??starts[0]);
      yearSelect.addEventListener('change',draw);
      const target=document.getElementById('housing-rows');
      [...rows].reverse().forEach(r=>{
        const tr=document.createElement('tr');
        [String(r.year),format.format(r.started),format.format(r.completed),r.partial?'Hittills i år (K1–K'+r.through_quarter+')':'Helår (K1–K4)'].forEach(value=>{
          const cell=document.createElement('td');cell.textContent=value;tr.append(cell);
        });
        target.append(tr);
      });
      document.getElementById('housing-data-area').hidden=false;
      draw();
      decorate();
    }catch(error){
      status.textContent='Bostadsstatistik kan ännu inte visas: '+error.message+'. Inga obekräftade värden visas.';
    }
  }
  init();
})();
