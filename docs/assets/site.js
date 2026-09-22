/* La Rose Parapharmacie — panier, recherche, filtres. Aucun paiement en ligne. */
(function () {
  var CUR = window.LR_CUR || 'DT', KEY = 'larose_cart_v1';
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };
  function money(n) { return n.toFixed(3).replace(/\.?0+$/, function (m) { return m === '.000' ? '' : m.replace(/0+$/, ''); }) + ' ' + CUR; }
  window.LRmoney = money;

  /* ---------- panier ---------- */
  function read() { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; } }
  function write(c) { try { localStorage.setItem(KEY, JSON.stringify(c)); } catch (e) {} paint(); }
  function count() { return read().reduce(function (n, i) { return n + i.q; }, 0); }
  function subtotal() { return read().reduce(function (n, i) { return n + i.p * i.q; }, 0); }
  window.LRcart = { read: read, write: write, subtotal: subtotal, count: count };

  function add(p, q) {
    var c = read(), f = null;
    for (var i = 0; i < c.length; i++) if (c[i].id === p.id) f = c[i];
    if (f) f.q += q || 1; else c.push({ id: p.id, n: p.n, b: p.b, p: p.p, img: p.img, u: p.u, q: q || 1 });
    write(c);
    toast('Ajouté au panier');
  }
  function setQty(id, q) {
    var c = read().map(function (i) { if (i.id === id) i.q = q; return i; }).filter(function (i) { return i.q > 0; });
    write(c);
  }
  function remove(id) { write(read().filter(function (i) { return i.id !== id; })); }

  var t;
  function toast(msg) {
    var el = $('#toast'); if (!el) return;
    el.querySelector('span').textContent = msg;
    el.classList.add('show'); clearTimeout(t);
    t = setTimeout(function () { el.classList.remove('show'); }, 2200);
  }

  function paint() {
    var n = count(), badge = $('#cart-count');
    if (badge) { badge.textContent = n; badge.hidden = n === 0; }
    var box = $('#drawer .items'), foot = $('#drawer .df');
    if (box) {
      var c = read();
      if (!c.length) {
        box.innerHTML = '<div class="emptycart"><svg viewBox="0 0 24 24"><circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path d="M2 3h3l2.6 12.4h11.2L21 7H6"/></svg><p>Votre panier est vide.</p></div>';
        if (foot) foot.innerHTML = '<a class="btn btn-line btn-block" href="' + R + 'catalogue.html">Parcourir le catalogue</a>';
      } else {
        box.innerHTML = c.map(function (i) {
          var th = i.img ? '<img src="' + R + i.img + '" alt="" loading="lazy">' : '<span class="ph">✿</span>';
          return '<div class="litem"><a class="thumb" href="' + R + i.u + '">' + th + '</a><div>' +
            '<small>' + esc(i.b || '') + '</small><a href="' + R + i.u + '"><b>' + esc(i.n) + '</b></a>' +
            '<div class="qs"><button data-dec="' + i.id + '" aria-label="Moins">−</button><span>' + i.q + '</span>' +
            '<button data-inc="' + i.id + '" aria-label="Plus">+</button></div>' +
            '<button class="rm" data-rm="' + i.id + '">Retirer</button></div>' +
            '<div class="lp">' + money(i.p * i.q) + '</div></div>';
        }).join('');
        if (foot) {
          foot.innerHTML = '<div class="sumrow"><span>Sous-total</span><b>' + money(subtotal()) + '</b></div>' +
            '<div class="sumrow muted" style="font-size:13px"><span>Livraison</span><span>calculée à la commande</span></div>' +
            '<a class="btn btn-rose btn-block" href="' + R + 'panier.html" style="margin-top:14px">Passer la commande</a>';
        }
      }
    }
    if (window.LRpaintCart) window.LRpaintCart();
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; }); }
  window.LResc = esc;
  var R = window.LR_ROOT || '';

  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-add]');
    if (a) {
      e.preventDefault();
      var q = 1, qi = $('#qty');
      if (a.hasAttribute('data-usa-qty') && qi) q = Math.max(1, parseInt(qi.value, 10) || 1);
      add(JSON.parse(a.getAttribute('data-add')), q);
      a.classList.add('done');
      setTimeout(function () { a.classList.remove('done'); }, 1100);
      return;
    }
    var d = e.target.closest('[data-dec]'), p = e.target.closest('[data-inc]'), r = e.target.closest('[data-rm]');
    if (d || p) {
      var id = (d || p).getAttribute(d ? 'data-dec' : 'data-inc');
      var it = read().filter(function (i) { return i.id === id; })[0];
      if (it) setQty(id, it.q + (d ? -1 : 1));
    }
    if (r) remove(r.getAttribute('data-rm'));
  });

  /* ---------- tiroirs ---------- */
  function openEl(sel) { var el = $(sel); if (el) { el.classList.add('open'); $('#scrim').classList.add('on'); document.body.style.overflow = 'hidden'; } }
  function closeAll() {
    ['#drawer', '#mobnav', '.facets'].forEach(function (s) { var el = $(s); if (el) el.classList.remove('open'); });
    var sb = $('#searchbox'); if (sb) sb.classList.remove('open');
    var sc = $('#scrim'); if (sc) sc.classList.remove('on');
    document.body.style.overflow = '';
  }
  window.LRclose = closeAll;
  document.addEventListener('click', function (e) {
    if (e.target.closest('#cart-open')) { e.preventDefault(); openEl('#drawer'); }
    if (e.target.closest('#nav-toggle')) { e.preventDefault(); openEl('#mobnav'); }
    if (e.target.closest('#filter-open')) { e.preventDefault(); openEl('.facets'); }
    if (e.target.closest('[data-close]') || e.target.id === 'scrim') { closeAll(); }
    if (e.target.closest('#search-open')) {
      e.preventDefault(); var sb = $('#searchbox');
      if (sb) { sb.classList.add('open'); document.body.style.overflow = 'hidden'; setTimeout(function () { $('#sq').focus(); }, 30); }
    }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeAll(); });

  /* ---------- recherche ---------- */
  var IDX = null, loading = false;
  function loadIndex(cb) {
    if (IDX) return cb(IDX);
    if (loading) return;
    loading = true;
    fetch(R + 'data/search.json').then(function (r) { return r.json(); }).then(function (j) { IDX = j; loading = false; cb(j); })
      .catch(function () { loading = false; });
  }
  window.LRindex = loadIndex;
  function norm(s) { return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  window.LRnorm = norm;
  function search(q, list, max) {
    var terms = norm(q).split(/\s+/).filter(Boolean);
    if (!terms.length) return [];
    var out = [];
    for (var i = 0; i < list.length; i++) {
      var h = list[i].s, ok = true, sc = 0;
      for (var j = 0; j < terms.length; j++) {
        var k = h.indexOf(terms[j]);
        if (k < 0) { ok = false; break; }
        sc += k === 0 ? 3 : (h[k - 1] === ' ' ? 2 : 1);
      }
      if (ok) { out.push([sc + (list[i].k ? 2 : 0), list[i]]); if (out.length > 600) break; }
    }
    out.sort(function (a, b) { return b[0] - a[0]; });
    return out.slice(0, max || 8).map(function (x) { return x[1]; });
  }
  window.LRsearch = search;

  var si = $('#sq');
  if (si) {
    var timer;
    si.addEventListener('input', function () {
      clearTimeout(timer);
      var q = si.value.trim();
      var box = $('#sresults');
      if (q.length < 2) { box.innerHTML = ''; return; }
      timer = setTimeout(function () {
        loadIndex(function (list) {
          var res = search(q, list, 9);
          box.innerHTML = res.length ? res.map(function (p) {
            var th = p.i ? '<img src="' + R + p.i + '" alt="" loading="lazy">' : '<span class="ph">✿</span>';
            return '<a href="' + R + p.u + '">' + th + '<span><b>' + esc(p.n) + '</b><small>' + esc(p.b || '') + '</small></span>' +
              '<span class="pr">' + money(p.p) + '</span></a>';
          }).join('') + '<a href="' + R + 'catalogue.html?q=' + encodeURIComponent(q) + '" style="justify-content:center;color:var(--rose-ink);font-size:14px;margin-top:6px">Voir tous les résultats →</a>'
            : '<p class="muted" style="padding:14px 12px">Aucun produit pour « ' + esc(q) + ' ». Écrivez-nous, nous pouvons le commander.</p>';
        });
      }, 140);
    });
    si.closest('form') && si.closest('form').addEventListener('submit', function (e) {
      e.preventDefault();
      if (si.value.trim()) location.href = R + 'catalogue.html?q=' + encodeURIComponent(si.value.trim());
    });
  }

  /* ---------- quantité (fiche produit) ---------- */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-q]'); if (!b) return;
    var i = $('#qty'); if (!i) return;
    i.value = Math.max(1, (parseInt(i.value, 10) || 1) + (b.getAttribute('data-q') === '+' ? 1 : -1));
  });

  paint();
})();

/* ---------- Carte Rose : fidélité (pétales), état local + repris dans chaque commande ---------- */
(function(){
  var K='larose_rose_v1', STEP=250, BON=15;
  function get(){ try{ return JSON.parse(localStorage.getItem(K))||{petals:0,orders:0,hist:[]}; }catch(e){ return {petals:0,orders:0,hist:[]}; } }
  function set(s){ try{ localStorage.setItem(K,JSON.stringify(s)); }catch(e){} paint(); return s; }
  function code(tel){ var d=String(tel||'').replace(/\D/g,''); return d.length>=4?'ROSE-'+d.slice(-4):''; }
  function stage(p){ return p<STEP*0.4?'Bouton de rose':p<STEP*0.8?'Éclosion':'Rose épanouie'; }
  function bons(p){ return Math.floor(p/STEP); }
  window.LRloyal={get:get,set:set,code:code,STEP:STEP,BON:BON,bons:bons,stage:stage,
    credit:function(amount,extra){ var s=get(); var add=Math.floor(amount)+(extra||0); s.petals+=add; s.orders+=1;
      s.hist.unshift({d:new Date().toISOString().slice(0,10),a:amount,p:add}); s.hist=s.hist.slice(0,30); return set(s); },
    redeem:function(){ var s=get(); if(s.petals>=STEP){ s.petals-=STEP; s.used=(s.used||0)+1; } return set(s); }
  };
  /* rose SVG : 12 pétales qui se colorent avec la progression vers le prochain bon */
  function roseSVG(id){
    var petals='';
    for(var i=0;i<12;i++){
      var a=i*30+(i<6?0:15), rx=i<6?40:30, ry=i<6?66:50, off=i<6?52:38;
      petals+='<ellipse class="pt" data-i="'+i+'" cx="120" cy="'+(120-off)+'" rx="'+rx+'" ry="'+ry+'" transform="rotate('+a+' 120 120)"/>';
    }
    return '<svg id="'+id+'" viewBox="-6 -6 252 252" aria-hidden="true">'+
      '<path class="leaf" d="M120 236c-26 6-46-12-52-36 26-4 46 10 52 36z"/><path class="leaf" d="M120 236c26 6 46-12 52-36-26-4-46 10-52 36z"/>'+
      petals+'<circle class="core" cx="120" cy="120" r="18"/><path d="M112 120a8 8 0 0116 0 8 8 0 01-16 0" fill="none" stroke="#d45c79" stroke-width="1.4"/></svg>';
  }
  window.LRroseSVG=roseSVG;
  function paint(){
    var s=get(), inCycle=s.petals%STEP, ratio=inCycle/STEP;
    document.querySelectorAll('svg[data-rose]').forEach(function(svg){
      var on=Math.round(ratio*12);
      svg.querySelectorAll('.pt').forEach(function(p,i){ var k=(i<6?i*2:(i-6)*2+1); p.classList.toggle('on',k<on); p.classList.toggle('deep',k<on&&k%3===0); });
    });
    document.querySelectorAll('[data-rose-petals]').forEach(function(e){ e.textContent=s.petals; });
    document.querySelectorAll('[data-rose-stage]').forEach(function(e){ e.textContent=stage(inCycle); });
    document.querySelectorAll('[data-rose-bar]').forEach(function(e){ e.style.width=(ratio*100)+'%'; });
    document.querySelectorAll('[data-rose-next]').forEach(function(e){ e.textContent=(STEP-inCycle); });
    document.querySelectorAll('[data-rose-bons]').forEach(function(e){ e.textContent=bons(s.petals); });
    document.querySelectorAll('[data-rose-orders]').forEach(function(e){ e.textContent=s.orders; });
    document.querySelectorAll('[data-rose-code]').forEach(function(e){ e.textContent=code(s.tel)||'— activez votre carte —'; });
    document.querySelectorAll('[data-rose-name]').forEach(function(e){ e.textContent=s.name?s.name:'et bienvenue'; });
    if(window.LRloyalPaint) window.LRloyalPaint(s);
  }
  window.LRloyalRepaint=paint;
  document.addEventListener('DOMContentLoaded',paint);
})();
