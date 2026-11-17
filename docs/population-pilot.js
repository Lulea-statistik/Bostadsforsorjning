'use strict';
(() => {
  const body = document.getElementById('indicators');
  const detail = document.getElementById('population-detail');
  const close = document.getElementById('population-detail-close');
  if (!body || !detail || !close) return;
  let trigger = null;
  let observations = [];
  const format = new Intl.NumberFormat('sv-SE');
  const source = 'data/population.json';

  function latestValue() {
    const last = observations.at(-1);
    return last && Number.isFinite(last.change) ? format.format(last.change) + ' (' + last.year + ')' : 'Ej inläst';
  }
  function decorate() {
    for (const row of body.rows) {
      if (row.cells[0]?.textContent.trim() !== 'Befolkningsökning') continue;
      if (!row.dataset.indicatorDetail) {
        row.dataset.indicatorDetail = 'population';
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'indicator-open';
        button.textContent = 'Befolkningsökning';
        button.setAttribute('aria-controls', 'population-detail');
        row.cells[0].replaceChildren(button);
      }
      if (observations.length) row.cells[2].textContent = latestValue();
    }
    sync();
  }
  function sync() {
    body.querySelectorAll('.indicator-open').forEach(b => b.setAttribute('aria-expanded', String(!detail.hidden)));
  }
  function show(button) {
    trigger = button;
    detail.hidden = false;
    sync();
    detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  function hide() {
    detail.hidden = true;
    sync();
    if (trigger?.isConnected) trigger.focus();
  }
  function svgElement(tag, attributes = {}, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attributes).forEach(([k, v]) => node.setAttribute(k, String(v)));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function drawChart(fromYear) {
    const svg = document.getElementById('population-change-chart');
    svg.replaceChildren();
    const selected = observations.filter(d => d.year >= fromYear && Number.isFinite(d.change));
    if (!selected.length) return;
    const W = 900, H = 320, left = 72, right = 18, top = 25, bottom = 45;
    const plotW = W - left - right, plotH = H - top - bottom;
    const largest = Math.max(100, ...selected.map(d => Math.abs(d.change)));
    const bound = Math.ceil(largest / 100) * 100;
    const y = v => top + (bound - v) / (bound * 2) * plotH;
    const zero = y(0);
    [-bound, -bound / 2, 0, bound / 2, bound].forEach(value => {
      const ypos = y(value);
      svg.append(svgElement('line', { x1: left, y1: ypos, x2: W-right, y2: ypos, class: 'axis', 'stroke-dasharray': value === 0 ? 'none' : '3 5' }));
      svg.append(svgElement('text', { x: left-9, y: ypos+4, 'text-anchor': 'end' }, format.format(value)));
    });
    const step = plotW / selected.length;
    selected.forEach((d, i) => {
      const x = left + i * step + step * .12;
      const valueY = y(d.change);
      const rect = svgElement('rect', {
        x, y: Math.min(zero, valueY), width: Math.max(1, step * .76),
        height: Math.max(1, Math.abs(valueY-zero)),
        class: d.change >= 0 ? 'bar-positive' : 'bar-negative'
      });
      rect.append(svgElement('title', {}, d.year + ': ' + (d.change > 0 ? '+' : '') + format.format(d.change) + ' personer (folkmängd ' + format.format(d.population) + ')'));
      svg.append(rect);
      const every = Math.max(1, Math.ceil(selected.length / 12));
      if (i % every === 0 || i === selected.length - 1) svg.append(svgElement('text', { x: x+step*.38, y: H-17, 'text-anchor': 'middle' }, String(d.year)));
    });
    svg.prepend(svgElement('title', {}, 'Luleås årliga befolkningsförändring ' + selected[0].year + '–' + selected.at(-1).year));
  }
  async function loadPopulation() {
    const status = document.getElementById('population-status');
    try {
      const response = await fetch(source, { cache: 'no-cache' });
      if (!response.ok) throw new Error('Datakällan är ännu inte publicerad');
      const json = await response.json();
      if (json.municipality !== '2580' || !Array.isArray(json.data)) throw new Error('Felaktigt dataformat');
      const rows = json.data.filter(d => Number.isInteger(d.year) && Number.isInteger(d.population) && (d.change === null || Number.isInteger(d.change))).sort((a,b) => a.year-b.year);
      if (!rows.length || rows.at(-1).year < 2025 || rows.some((d, i) => i && d.year === rows[i-1].year)) throw new Error('Ofullständig eller överlappande årsserie');
      observations = rows;
      const last = rows.at(-1);
      status.textContent = 'Senaste årsutfall: ' + (last.change >= 0 ? '+' : '') + latestValue() + ' personer. Folkmängd: ' + format.format(last.population) + ' personer den 31 december ' + last.year + '.';
      const years = document.getElementById('population-year-from');
      [1970, 1990, 2000, 2010, 2020].filter(y => y <= last.year).forEach(year => {
        const option = document.createElement('option'); option.value = String(year); option.textContent = String(year); years.append(option);
      });
      years.value = '2000';
      years.addEventListener('change', () => drawChart(Number(years.value)));
      document.getElementById('population-chart-area').hidden = false;
      document.getElementById('population-method-note').textContent = json.method_note || '';
      const table = document.getElementById('population-data-rows');
      [...rows].reverse().forEach(d => {
        const tr = document.createElement('tr');
        [String(d.year), format.format(d.population), d.change === null ? '–' : (d.change > 0 ? '+' : '') + format.format(d.change)].forEach(value => {
          const td = document.createElement('td'); td.textContent = value; tr.append(td);
        });
        table.append(tr);
      });
      drawChart(Number(years.value));
      decorate();
    } catch (error) {
      status.textContent = 'Årsstatistiken är ännu inte tillgänglig. Inga värden visas innan import och kontroll har lyckats (' + error.message + ').';
    }
  }
  body.addEventListener('click', event => {
    const row = event.target.closest('tr[data-indicator-detail="population"]');
    if (!row) return;
    const button = row.querySelector('.indicator-open');
    if (!button) return;
    detail.hidden ? show(button) : hide();
  });
  close.addEventListener('click', hide);
  new MutationObserver(decorate).observe(body, { childList: true });
  decorate();
  loadPopulation();
})();
