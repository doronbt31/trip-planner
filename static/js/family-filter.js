/**
 * Family Filter — welcome overlay + per-page leg filtering.
 *
 * Three modes stored in localStorage('trip_family'):
 *   bartov → Copenhagen + Cruise (Aug 6–16)
 *   perek  → Austria Flachau + Großarl (Aug 16–25)
 *   both   → Full trip
 *
 * Pages opt-in by adding data-filter-leg="<leg_id>" to any element.
 */
(function () {
  'use strict';

  const KEY = 'trip_family';

  const FAMILIES = {
    bartov: {
      label: 'Bartov Family',
      legs: ['copenhagen_pre', 'cruise'],
      emoji: '🚢',
      desc: 'Copenhagen + Norway Cruise · Aug 6–16',
      color: '#378ADD',
    },
    perek: {
      label: 'Perek Family',
      legs: ['austria_flachau', 'grossarl'],
      emoji: '🏔️',
      desc: 'Austria Mountains · Aug 16–25',
      color: '#3aaa5e',
    },
    both: {
      label: 'Full Crew',
      legs: ['copenhagen_pre', 'cruise', 'austria_flachau', 'grossarl'],
      emoji: '✈️',
      desc: 'The whole trip · Aug 6–25',
      color: '#8b5cf6',
    },
  };

  // ── Filter ────────────────────────────────────────────────────────────────

  function applyFilter(key) {
    const family = FAMILIES[key] || FAMILIES.both;
    document.querySelectorAll('[data-filter-leg]').forEach(function (el) {
      var leg = el.dataset.filterLeg;
      el.style.display = family.legs.indexOf(leg) !== -1 ? '' : 'none';
    });
    renderNavBadge(key);
  }

  // ── Nav badge ─────────────────────────────────────────────────────────────

  function renderNavBadge(key) {
    var existing = document.getElementById('fam-badge');
    if (existing) existing.remove();

    var nav = document.querySelector('nav');
    if (!nav) return;

    var family = FAMILIES[key] || FAMILIES.both;
    var btn = document.createElement('button');
    btn.id = 'fam-badge';
    btn.title = 'Change family view';
    btn.innerHTML = family.emoji + ' <span style="font-size:0.75rem">' + family.label + '</span>';
    btn.style.cssText = [
      'margin-left:auto',
      'background:rgba(255,255,255,0.13)',
      'border:1px solid rgba(255,255,255,0.22)',
      'border-radius:20px',
      'color:#fff',
      'padding:3px 12px',
      'font-size:0.82rem',
      'cursor:pointer',
      'display:flex',
      'align-items:center',
      'gap:5px',
      'font-family:inherit',
      'white-space:nowrap',
    ].join(';');
    btn.onmouseover = function () { btn.style.background = 'rgba(255,255,255,0.22)'; };
    btn.onmouseout  = function () { btn.style.background = 'rgba(255,255,255,0.13)'; };
    btn.onclick = showOverlay;
    nav.appendChild(btn);
  }

  // ── Overlay ───────────────────────────────────────────────────────────────

  function showOverlay() {
    var ov = document.getElementById('fam-overlay');
    if (ov) ov.style.display = 'flex';
  }

  function hideOverlay() {
    var ov = document.getElementById('fam-overlay');
    if (ov) ov.style.display = 'none';
  }

  function selectFamily(key) {
    localStorage.setItem(KEY, key);
    applyFilter(key);
    hideOverlay();
  }
  window._tripSelectFamily = selectFamily;

  function createOverlay() {
    var ov = document.createElement('div');
    ov.id = 'fam-overlay';
    ov.style.cssText = [
      'display:none',
      'position:fixed',
      'inset:0',
      'background:rgba(10,10,30,0.9)',
      'z-index:9999',
      'align-items:center',
      'justify-content:center',
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
    ].join(';');

    var cards = Object.entries(FAMILIES).map(function (entry) {
      var k = entry[0], f = entry[1];
      return [
        '<button onclick="window._tripSelectFamily(\'' + k + '\')"',
        ' style="display:flex;align-items:center;gap:14px;padding:14px 18px;',
        'border-radius:12px;border:2px solid #e8e8e8;background:#fafafa;',
        'cursor:pointer;text-align:left;width:100%;font-family:inherit;',
        'transition:all 0.15s;"',
        ' onmouseover="this.style.borderColor=\'' + f.color + '\';this.style.background=\'#f5faff\'"',
        ' onmouseout="this.style.borderColor=\'#e8e8e8\';this.style.background=\'#fafafa\'"',
        '>',
        '<span style="font-size:1.8rem">' + f.emoji + '</span>',
        '<div>',
        '<div style="font-size:0.95rem;font-weight:700;color:#1a1a2e">' + f.label + '</div>',
        '<div style="font-size:0.8rem;color:#888;margin-top:3px">' + f.desc + '</div>',
        '</div>',
        '</button>',
      ].join('');
    }).join('');

    ov.innerHTML = [
      '<div style="background:#fff;border-radius:20px;padding:36px 28px 32px;',
      'max-width:400px;width:90%;text-align:center;',
      'box-shadow:0 24px 64px rgba(0,0,0,0.45);">',
      '<div style="font-size:2.8rem;margin-bottom:10px">🌍</div>',
      '<h2 style="font-size:1.25rem;font-weight:700;color:#1a1a2e;margin-bottom:6px">',
      'Family Summer Trip 2026</h2>',
      '<p style="font-size:0.88rem;color:#888;margin-bottom:26px">',
      'Which part of the trip are you joining?</p>',
      '<div style="display:flex;flex-direction:column;gap:10px">',
      cards,
      '</div>',
      '</div>',
    ].join('');

    document.body.appendChild(ov);
  }

  // ── Init ──────────────────────────────────────────────────────────────────

  function init() {
    createOverlay();
    var saved = localStorage.getItem(KEY);
    if (!saved) {
      showOverlay();
    } else {
      applyFilter(saved);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
