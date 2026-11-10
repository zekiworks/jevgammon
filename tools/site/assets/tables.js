'use strict';

/* Every page: tables come first and answer clicks.
   - Click (or Enter on) a column header to sort by it: ascending, then descending, then the build's order. Numbers sort
     as numbers (the small second line of a cell, such as an interval, is ignored); status words such as "Too few
     decisions" or "N/A" always go last. A header with data-nosort never sorts (Close choices: never ranked). A header
     with data-sort-default is the build's own order (it carries aria-sort at load): its clicks switch between the other
     direction and the build's order, which it marks with its default direction again.
   - Click a row to open what it is about: its data-href, else the first link in the row (a setup's page, a decision,
     a league). Clicks on links, buttons and form fields keep their own meaning; Ctrl/Cmd-click opens a new tab.
   - A link to an anchor inside a closed <details> opens it.
   Works for tables written later by other scripts (Every decision), through one listener on the document. */

(function tables() {
  const SKIP = '.small, .mark, .nm, .status';

  function key(td) {
    if (!td) return null;
    if (td.dataset.v !== undefined) return Number(td.dataset.v);
    let text = '';
    td.childNodes.forEach(n => {
      if (n.nodeType === Node.TEXT_NODE) text += n.textContent;
      else if (n.nodeType === Node.ELEMENT_NODE && !n.matches(SKIP)) text += n.textContent;
    });
    text = text.trim();
    if (!text) {
      const status = td.querySelector('.status');
      return status ? status.textContent.trim().toLowerCase() : null;
    }
    const m = text.replace(/\u2212/g, '-').replace(/[,$%\u00a0]/g, '').match(/^[-+]?\d*\.?\d+(?:e[-+]?\d+)?/i);
    return m ? parseFloat(m[0]) : text.toLowerCase();
  }

  function compare(a, b) {
    if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
    if (typeof a === 'number' && typeof b === 'number') return a - b;
    if (typeof a === 'number') return -1;
    if (typeof b === 'number') return 1;
    return a.localeCompare(b, 'en', { numeric: true });
  }

  function sortBy(th) {
    const table = th.closest('table');
    const body = table && table.tBodies[0];
    if (!body || body.rows.length < 2 || body.querySelector('td[colspan]')) return;
    const col = Array.prototype.indexOf.call(th.parentNode.children, th);
    const state = th.getAttribute('aria-sort');
    const initial = th.dataset.sortDefault;
    const next = initial ? (state === initial ? (initial === 'descending' ? 'ascending' : 'descending') : 'none')
      : state === 'ascending' ? 'descending' : state === 'descending' ? 'none' : 'ascending';
    th.parentNode.querySelectorAll('th').forEach(h => h.removeAttribute('aria-sort'));
    const rows = Array.from(body.rows);
    rows.forEach((r, i) => { if (r.dataset.order === undefined) r.dataset.order = i; });
    if (next === 'none') {
      // The build's order: a table whose order is a column's default sort shows that column's state again.
      rows.sort((a, b) => a.dataset.order - b.dataset.order);
      const d = th.parentNode.querySelector('[data-sort-default]');
      if (d) d.setAttribute('aria-sort', d.dataset.sortDefault);
    } else {
      th.setAttribute('aria-sort', next);
      const sign = next === 'ascending' ? 1 : -1;
      rows.sort((a, b) => {
        const ka = key(a.cells[col]);
        const kb = key(b.cells[col]);
        if (ka === null || kb === null) return compare(ka, kb);
        return sign * compare(ka, kb) || a.dataset.order - b.dataset.order;
      });
    }
    rows.forEach(r => body.appendChild(r));
  }

  function prepare(root) {
    root.querySelectorAll('thead th:not([tabindex]):not([data-nosort])').forEach(th => {
      th.tabIndex = 0;
      th.title = 'Sort by this column';
    });
  }

  document.addEventListener('click', event => {
    const th = event.target.closest('thead th');
    if (th) { if (!th.hasAttribute('data-nosort')) sortBy(th); return; }
    const row = event.target.closest('tbody tr');
    // A click the row's own handler took (the leaderboard's tap that opens a details box, bg.js) does not navigate;
    // nor does a tap on a tooltip (.hint: the own-machine cost explanation opens on focus instead).
    if (!row || event.defaultPrevented || event.target.closest('a, button, select, input, label, summary, .hint')) return;
    if (String(window.getSelection())) return;
    const link = row.dataset.href || row.querySelector('a[href]')?.getAttribute('href');
    if (!link) return;
    const url = new URL(link, location.href);
    if (event.ctrlKey || event.metaKey) window.open(url, '_blank');
    else location.href = url;
  });
  document.addEventListener('keydown', event => {
    const th = event.target.closest && event.target.closest('thead th');
    if (th && !th.hasAttribute('data-nosort') && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); sortBy(th); }
  });

  prepare(document);
  let pending = false;
  new MutationObserver(() => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { pending = false; prepare(document); });
  }).observe(document.body, { childList: true, subtree: true });

  function openTarget() {
    const id = decodeURIComponent(location.hash.slice(1));
    const target = id && document.getElementById(id);
    if (!target) return;
    let d = target.closest('details');
    while (d) { d.open = true; d = d.parentElement.closest('details'); }
    target.scrollIntoView();
  }
  window.addEventListener('hashchange', openTarget);
  openTarget();
})();

/* A row's details box (Ümit #2904, as Clocktower Bench's; moved here from bg.js so every page has it, Ümit #4425
   JOB 8). A tap on a phone opens it and a second tap on the row, a tap outside it or Escape closes it; with a mouse it
   shows while the pointer is on the row or its box (150 ms of grace after leaving both, so the pointer can cross a
   corner into the box; another row takes over at once); with the keyboard while the focus is in the row (the model's
   name, then the box's links). Where the window has room the box stands beside its row, right of the score column (the
   third; else right of the name column), from the row's top (from its bottom upwards near the window's foot): it never
   covers another row's name, so the row under the pointer on a name is the row whose box shows (HoverCheck, Zeki
   #3146). On a phone it goes under the row (above it near the bottom of the window). Within the window's width;
   capped where it does not fit. Without JavaScript every box is shown in its row. Rows name their box in data-box. */
window.rowDetails = function rowDetails(table) {
  if (table.dataset.rowDetails) return;
  table.dataset.rowDetails = 'on';
  let open = null, pinned = false, pointer = 'mouse', quiet = false;
  const boxOf = tr => (tr.dataset.box ? document.getElementById(tr.dataset.box) : null);
  const place = () => {
    if (!open) return;
    const box = boxOf(open);
    if (!box) return;
    const nameCell = open.querySelector('.model') || open.cells[0];
    const row = open.getBoundingClientRect(), cell = nameCell.getBoundingClientRect();
    const score = open.cells[Math.min(2, open.cells.length - 1)].getBoundingClientRect();
    const vw = document.documentElement.clientWidth;  // the visible width, even where something overflows the page
    const width = Math.min(380, vw - 16);
    box.style.width = `${width}px`;
    box.style.maxHeight = '';
    let height = box.offsetHeight;
    const headerEl = document.querySelector('.site-header');
    const header = headerEl && !headerEl.classList.contains('is-tucked') ? Math.max(0, headerEl.getBoundingClientRect().bottom) : 0;
    const bottom = innerHeight - 8;
    const side = vw - 8 - score.right >= width ? score.right : vw - 8 - cell.right >= width ? cell.right : null;
    if (side !== null) {
      // Beside the row: from its top, else ending at its bottom; where neither fits, within the window as near the
      // row as it goes, capped to the window under the header (scrolling inside).
      box.style.left = `${side}px`;
      const top = header + 4;
      if (height > bottom - top) { height = Math.max(bottom - top, 80); box.style.maxHeight = `${height}px`; }
      box.style.top = `${row.top >= top && row.top + height <= bottom ? row.top
        : row.bottom - height >= top && row.bottom <= bottom ? row.bottom - height
        : Math.min(Math.max(row.top, top), bottom - height)}px`;
      return;
    }
    box.style.left = `${Math.max(8, Math.min(cell.left, vw - width - 8))}px`;
    // Height: below the row if it fits, else above it. If it fits neither way, capped to the larger side of the row,
    // scrolling inside (its links stay reachable by scrolling it or with Tab), so the row itself stays uncovered for a
    // second tap; only where neither side has 120 px does it take the window under the header.
    const below = row.bottom;  // no gap: the pointer moves from the row into its box without leaving the row
    const roomBelow = bottom - below, roomAbove = row.top - header - 4;
    if (height <= roomBelow) box.style.top = `${below}px`;
    else if (height <= roomAbove) box.style.top = `${row.top - height}px`;
    else if (Math.max(roomBelow, roomAbove) >= 120) {
      box.style.maxHeight = `${Math.max(roomBelow, roomAbove)}px`;
      box.style.top = `${roomBelow >= roomAbove ? below : row.top - roomAbove}px`;
    } else {
      const room = Math.max(bottom - header - 4, 80);
      box.style.maxHeight = `${room}px`;
      box.style.top = `${header + 4}px`;
    }
  };
  const hide = () => {
    if (!open) return;
    const box = boxOf(open);
    if (box) box.classList.remove('open');
    open.classList.remove('hl-open');
    open = null;
    pinned = false;
  };
  const show = (tr, pin) => {
    if (open !== tr) hide();
    const box = boxOf(tr);
    if (!box) return;
    open = tr;
    pinned = pin;
    tr.classList.add('hl-open');
    box.classList.add('open');
    place();
  };
  const inTable = target => target instanceof Element && target.closest('table') === table;
  const rowOf = target => {
    const tr = target instanceof Element && target.closest('tbody tr[data-box]');
    return tr && inTable(tr) ? tr : null;
  };
  // Keyboard focus in the open row (its name or its box) keeps the box: the pointer leaving the row or entering another
  // row does not take it away until the focus leaves the row, Escape, a second tap or a click outside. Focus that a
  // press of the pointer gives (pointing) neither opens a box nor holds one: the press itself decides.
  let pointing = false, keyed = false;
  const held = () => !!open && keyed && open.contains(document.activeElement);
  document.addEventListener('pointerdown', event => {
    pointing = true;
    if (table.contains(event.target)) pointer = event.pointerType || 'mouse';
  }, true);
  const released = () => setTimeout(() => { pointing = false; });
  document.addEventListener('pointerup', released, true);
  document.addEventListener('pointercancel', released, true);
  // The pointer leaving the row and its box (the box is inside the row) closes it after a 150 ms grace; entering the row
  // or its box again keeps it, entering another row shows that row's box at once. Listeners sit on the table, so rows
  // that get their box later (phone tables, below) take part too.
  let leaving = 0;
  const stay = () => { clearTimeout(leaving); leaving = 0; };
  table.addEventListener('pointerover', event => {
    const tr = rowOf(event.target);
    if (event.pointerType !== 'mouse' || !tr) return;
    stay();
    if (!pinned && !held() && open !== tr) show(tr, false);
  });
  table.addEventListener('pointerout', event => {
    const tr = rowOf(event.target);
    if (event.pointerType !== 'mouse' || !tr || pinned || open !== tr || held() || tr.contains(event.relatedTarget)) return;
    stay();
    leaving = setTimeout(() => { leaving = 0; if (open === tr && !pinned && !held()) hide(); }, 150);
  });
  table.addEventListener('focusin', event => {
    const tr = rowOf(event.target);
    // A cost tooltip (.hint) takes the focus to show itself (a tap focuses it after the pointer is up): not the box.
    if (!tr || event.target.closest('.hint')) return;
    keyed = !pointing;
    if (keyed && open !== tr && !quiet) show(tr, false);
  });
  table.addEventListener('focusout', event => {
    const tr = rowOf(event.target);
    if (tr && open === tr && !pinned && !tr.contains(event.relatedTarget)) hide();
  });
  table.addEventListener('click', event => {
    const tr = rowOf(event.target);
    const box = tr && boxOf(tr);
    // A mouse click or a key (detail 0) follows the link; a link or key in the box or the expander does its own job.
    // A cost tooltip (.hint) opens on its own tap (focus), not the row's box.
    if (!box || pointer === 'mouse' || event.detail === 0 || box.contains(event.target) || event.target.closest('.hl-more, .hint')) return;
    event.preventDefault();  // a tap opens the box (the row click below leaves a prevented click alone)
    if (open === tr && pinned) hide(); else show(tr, true);
  });
  document.addEventListener('click', event => { if (open && !open.contains(event.target)) hide(); });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !open) return;
    const name = open.querySelector('.model-name');
    const inside = open.contains(document.activeElement);
    hide();
    if (inside && name) { quiet = true; name.focus(); quiet = false; }
  });
  addEventListener('scroll', place, { passive: true });
  addEventListener('resize', place);
  table.addEventListener('hl-filter', () => { if (open && open.classList.contains('hl-off')) hide(); });
  table.addEventListener('row-details-reset', hide);
};
document.querySelectorAll('#headline-table, #improve-results-table').forEach(t => window.rowDetails(t));

/* Tables on a phone (below 768 px; Ümit #4425 JOB 8): the page scrolls, never a box inside it. A table wider than its
   frame keeps, per row, the rank (and Tier), the model or setup name, the main score and the cost; every other column
   goes into the row's details box (the component above), as "column: value", with the tooltips of the cells kept in
   view (a score's 95% interval). The leaderboard and the "Did they improve?" table have their own boxes and layouts
   (bg.css). A table with merged header cells keeps all its columns and wraps them. Back on a wide screen every column
   returns. */
(function phoneTables() {
  const phone = matchMedia('(max-width: 767px)');
  const OWN = '#headline-table, #improve-results-table';
  let made = 0;
  const heads = table => {
    const rows = table.tHead ? table.tHead.rows : [];
    return rows.length ? [...rows[rows.length - 1].cells] : [];
  };
  const plain = table => {
    const h = heads(table);
    return h.length > 2 && table.tHead.rows.length === 1 && !h.some(c => c.colSpan > 1 || c.rowSpan > 1)
      && ![...table.tBodies].some(b => [...b.rows].some(r => r.cells.length > 1 && [...r.cells].some(c => c.colSpan > 1 || c.rowSpan > 1)));
  };
  const label = th => (th.dataset.label || th.textContent).replace(/\s+/g, ' ').trim();
  const keepOf = h => {
    const text = h.map(label);
    const keep = new Set([0]);
    text.forEach((t, i) => { if (/^(#|rank\b|tier\b)/i.test(t)) keep.add(i); });
    const name = text.findIndex(t => /\b(model|setup|name)\b/i.test(t));
    if (name >= 0) keep.add(name);
    // The main score: the first of these kinds a header names (a paired test's drop before its two error rates).
    const kinds = [/judgement/i, /\bdrop\b/i, /\bchange\b/i, /improved/i, /error rate|\bPR\b/i, /\bscore|accuracy|best play/i];
    const score = kinds.map(re => text.findIndex((t, i) => !keep.has(i) && re.test(t))).find(i => i >= 0);
    const firstNum = h.findIndex((c, i) => !keep.has(i) && c.classList.contains('num'));
    if (score !== undefined) keep.add(score); else if (firstNum >= 0) keep.add(firstNum);
    const cost = text.findIndex(t => /\$|\bcost\b/i.test(t));
    if (cost >= 0) keep.add(cost);
    return keep;
  };
  const undo = table => {
    table.querySelectorAll('.ph-off').forEach(c => c.classList.remove('ph-off'));
    table.querySelectorAll('tr[data-ph-box]').forEach(tr => {
      document.getElementById(tr.dataset.box)?.remove();
      delete tr.dataset.box;
      delete tr.dataset.phBox;
    });
    table.classList.remove('ph-fit');
    table.dispatchEvent(new CustomEvent('row-details-reset'));
  };
  const fit = table => {
    const h = heads(table);
    const keep = keepOf(h);
    table.classList.add('ph-fit');  // its cells wrap
    if (keep.size >= h.length) return;
    h.forEach((c, i) => c.classList.toggle('ph-off', !keep.has(i)));
    [...table.tBodies].forEach(b => [...b.rows].forEach(tr => {
      if (tr.cells.length !== h.length) return;
      const lines = [];
      [...tr.cells].forEach((c, i) => {
        if (!keep.has(i)) c.classList.add('ph-off');
        const v = c.textContent.replace(/\s+/g, ' ').trim();
        const tip = c.getAttribute('title');
        if (i === 0) lines.unshift(`<p><strong>${esc(v)}</strong></p>`);
        else if (!keep.has(i) && (v || tip)) lines.push(`<p>${esc(label(h[i]))}: ${esc(v)}${tip ? ` (${esc(tip)})` : ''}</p>`);
        else if (tip) lines.push(`<p>${esc(label(h[i]))}: ${esc(v)} (${esc(tip)})</p>`);
      });
      if (lines.length < 2) return;
      const link = tr.dataset.href || tr.querySelector('a[href]')?.getAttribute('href');
      if (link) lines.push(`<p><a href="${esc(link)}">Open \u2192</a></p>`);
      const box = document.createElement('div');
      box.className = 'hl-box ph-box';
      box.id = `ph-box-${++made}`;
      box.setAttribute('role', 'group');
      box.innerHTML = lines.join('');
      tr.cells[0].appendChild(box);
      tr.dataset.box = box.id;
      tr.dataset.phBox = '1';
    }));
    window.rowDetails(table);
  };
  const esc = s => s.replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
  const run = () => {
    document.querySelectorAll('table').forEach(table => {
      if (table.matches(OWN) || table.closest('.hl-box, .no-phone-fit')) return;
      if (!phone.matches) { if (table.classList.contains('ph-fit')) undo(table); return; }
      if (table.classList.contains('ph-fit') || !table.offsetParent || !plain(table)) return;
      const frame = table.parentElement;
      if (table.scrollWidth > frame.clientWidth + 1 || table.offsetWidth > document.documentElement.clientWidth) fit(table);
    });
  };
  let queued = false;
  const soon = () => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; run(); }); } };
  run();
  phone.addEventListener('change', run);
  addEventListener('resize', soon);
  // Tables shown later (a tab, a view key, an opened fold) or written by a page's script.
  document.addEventListener('click', soon);
  document.addEventListener('toggle', soon, true);
  new MutationObserver(soon).observe(document.body, { childList: true, subtree: true });
})();

/* A tooltip key (.hint, e.g. an own-machine cost's explanation) shows while it has the focus: Escape closes it, as a tap
   outside it does (the focus leaves it). */
document.addEventListener('keydown', event => {
  const hint = event.key === 'Escape' && document.activeElement && document.activeElement.closest('.hint');
  if (hint) hint.blur();
});
