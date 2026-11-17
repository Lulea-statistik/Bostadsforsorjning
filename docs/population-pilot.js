'use strict';
// Accessible pilot: only the population-change row opens a detail panel.
(() => {
  const body = document.getElementById('indicators');
  const detail = document.getElementById('population-detail');
  const close = document.getElementById('population-detail-close');
  if (!body || !detail || !close) return;
  let trigger = null;
  const decorate = () => {
    for (const row of body.rows) {
      if (row.cells[0]?.textContent.trim() !== 'Befolkningsökning') continue;
      if (row.dataset.indicatorDetail === 'population') continue;
      row.dataset.indicatorDetail = 'population';
      const first = row.cells[0];
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'indicator-open';
      button.textContent = 'Befolkningsökning';
      button.setAttribute('aria-controls', 'population-detail');
      button.setAttribute('aria-expanded', String(!detail.hidden));
      first.replaceChildren(button);
    }
  };
  const sync = () => {
    body.querySelectorAll('.indicator-open').forEach(b => b.setAttribute('aria-expanded', String(!detail.hidden)));
  };
  const show = (button) => {
    trigger = button;
    detail.hidden = false;
    sync();
    detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };
  const hide = () => {
    detail.hidden = true;
    sync();
    if (trigger?.isConnected) trigger.focus();
  };
  body.addEventListener('click', (event) => {
    const row = event.target.closest('tr[data-indicator-detail="population"]');
    if (!row) return;
    const button = row.querySelector('.indicator-open');
    if (!button) return;
    if (detail.hidden) show(button);
    else hide();
  });
  close.addEventListener('click', hide);
  // Indicator rows are replaced when filters change.
  const observer = new MutationObserver(decorate);
  observer.observe(body, { childList: true });
  decorate();
})();
