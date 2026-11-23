export function bindSheet(table, display) {
  if (!table) return;
  const rows = [...table.tBodies[0].rows];
  const cells = rows.map(row => [...row.querySelectorAll('td')]);
  let current = cells[0][0];
  table.addEventListener('focusin', event => {
    const next = event.target.closest('td[data-cell]');
    if (!next) return;
    current.tabIndex = -1;
    next.tabIndex = 0;
    current = next;
    display.textContent = `${next.dataset.cell} · ${next.textContent.trim()}`;
  });
  table.addEventListener('click', event => {
    if (!event.target.closest('a')) event.target.closest('td')?.focus();
  });
  table.addEventListener('keydown', event => {
    const offset = {ArrowUp: [-1,0], ArrowDown: [1,0], ArrowLeft: [0,-1], ArrowRight: [0,1]}[event.key];
    if (!offset || event.target !== current) return;
    event.preventDefault();
    cells[current.parentElement.sectionRowIndex + offset[0]]?.[current.cellIndex - 1 + offset[1]]?.focus();
  });
}
