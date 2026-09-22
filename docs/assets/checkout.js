/* Finalisation de commande : validation, enregistrement (e-mail), confirmation. */
document.addEventListener('DOMContentLoaded', function () {
  var CFG = {"fee": 8.0, "free": 150.0, "wa": "21623979204", "mail": "inessaid88@gmail.com", "cc": "fatmazangar95@gmail.com", "days": "24 à 72 h", "city": "Nabeul", "addr": "Avenue Hédi Nouira"}, R = window.LR_ROOT || '';
  var $ = function (id) { return document.getElementById(id); };
  var form = $('order'), lines = $('cart-lines'), sum = $('sum'), empty = $('cart-empty');
  var money = function (n) { return window.LRmoney(n); };
  $('cart-rose').innerHTML = window.LRroseSVG('cr'); $('cr').setAttribute('data-rose', '');

  function mode() { var m = form.querySelector('input[name=mode]:checked'); return m ? m.value : 'livraison'; }
  function redeeming() { var r = $('redeem'); return !!(r && r.checked && window.LRloyal.get().petals >= window.LRloyal.STEP); }
  function totals() {
    var st = window.LRcart.subtotal();
    var deliv = (mode() === 'retrait' || st >= CFG.free || st === 0) ? 0 : CFG.fee;
    var red = redeeming() ? window.LRloyal.BON : 0;
    return { st: st, deliv: deliv, red: red, total: Math.max(0, st + deliv - red) };
  }
  function sumHTML(t) {
    var dl = mode() === 'retrait' ? 'Retrait en boutique' : (t.deliv === 0 ? 'Offerte' : money(t.deliv));
    return '<div class="sumrow"><span>Sous-total (' + window.LRcart.count() + ')</span><b>' + money(t.st) + '</b></div>' +
      '<div class="sumrow"><span>Livraison</span><span>' + dl + '</span></div>' +
      (t.red ? '<div class="sumrow" style="color:var(--rose-ink)"><span>Bon Carte Rose</span><span>−' + money(t.red) + '</span></div>' : '') +
      '<div class="sumrow total"><span>Total à régler</span><span>' + money(t.total) + '</span></div>';
  }
  window.LRpaintCart = function () {
    var c = window.LRcart.read(), t = totals(), ls = window.LRloyal.get();
    if (!c.length) { lines.innerHTML = ''; empty.style.display = 'block'; form.style.display = 'none'; }
    else {
      empty.style.display = 'none'; form.style.display = '';
      lines.innerHTML = c.map(function (i) {
        var th = i.img ? '<img src="' + R + i.img + '" alt="" loading="lazy">' : '<span class="ph">✿</span>';
        return '<div class="litem"><a class="thumb" href="' + R + i.u + '">' + th + '</a><div>' +
          '<small>' + window.LResc(i.b || '') + '</small><a href="' + R + i.u + '"><b>' + window.LResc(i.n) + '</b></a>' +
          '<div class="qs"><button type="button" data-dec="' + i.id + '">−</button><span>' + i.q + '</span><button type="button" data-inc="' + i.id + '">+</button></div>' +
          '<button type="button" class="rm" data-rm="' + i.id + '">Retirer</button></div><div class="lp">' + money(i.p * i.q) + '</div></div>';
      }).join('');
    }
    $('gain').textContent = Math.floor(t.st);
    $('redeem-row').style.display = ls.petals >= window.LRloyal.STEP ? 'flex' : 'none';
    if (ls.name && !$('prenom').value) $('prenom').value = ls.name;
    if (ls.tel && !$('tel').value) $('tel').value = ls.tel;
    sum.innerHTML = sumHTML(t);
  };

  form.addEventListener('change', function (e) {
    if (e.target.name === 'mode') {
      form.querySelectorAll('.opt').forEach(function (o) { o.classList.toggle('on', o.querySelector('input').checked); });
      $('addr').style.display = mode() === 'retrait' ? 'none' : '';
    }
    var f = e.target.closest('.field'); if (f) f.classList.remove('err');
    window.LRpaintCart();
  });

  function bad(id, test) { var f = $(id), w = f.closest('.field'), ok = test(f.value.trim()); w.classList.toggle('err', !ok); return !ok; }
  function validate() {
    var e = false;
    e = bad('nom', function (v) { return v.length > 2; }) || e;
    e = bad('tel', function (v) { return v.replace(/\D/g, '').length >= 8; }) || e;
    if (mode() !== 'retrait') {
      e = bad('gov', function (v) { return !!v; }) || e;
      e = bad('ville', function (v) { return v.length > 1; }) || e;
      e = bad('adresse', function (v) { return v.length > 4; }) || e;
    }
    if (e) { var f = form.querySelector('.field.err'); if (f) f.scrollIntoView({ block: 'center', behavior: 'smooth' }); }
    return !e;
  }

  function orderNumber() {
    var d = new Date(), p = function (n) { return (n < 10 ? '0' : '') + n; };
    return 'LR' + String(d.getFullYear()).slice(2) + p(d.getMonth() + 1) + p(d.getDate()) + '-' + Math.floor(1000 + Math.random() * 9000);
  }
  function orderText(num) {
    var c = window.LRcart.read(), t = totals(), L = window.LRloyal, ls = L.get();
    var nom = $('nom').value.trim(), tel = $('tel').value.trim();
    var s = 'COMMANDE ' + num + ' — La Rose Parapharmacie\n\n';
    c.forEach(function (i) { s += '• ' + i.n + (i.b ? ' (' + i.b + ')' : '') + ' × ' + i.q + ' — ' + money(i.p * i.q) + '\n'; });
    s += '\nSous-total : ' + money(t.st) + '\n';
    s += mode() === 'retrait' ? 'Mode : RETRAIT EN BOUTIQUE\n' : 'Livraison : ' + (t.deliv ? money(t.deliv) : 'offerte') + '\n';
    if (t.red) s += 'Bon Carte Rose : −' + money(t.red) + '\n';
    s += 'TOTAL À RÉGLER : ' + money(t.total) + ' (paiement à la réception)\n\n';
    s += 'Client : ' + nom + '\nTéléphone : ' + tel + '\n';
    if (mode() !== 'retrait') s += 'Adresse : ' + $('adresse').value.trim() + ', ' + $('ville').value.trim() + ', ' + $('gov').value + '\n';
    var n = $('notes').value.trim(); if (n) s += 'Instructions : ' + n + '\n';
    var pr = $('parrain').value.trim().toUpperCase();
    s += '\nCarte Rose ' + L.code(tel) + ' : ' + ls.petals + ' pétales → ' + (ls.petals - (t.red ? L.STEP : 0) + Math.floor(t.st)) + ' après' + (ls.orders === 0 ? ' · 1ère commande (cadeau de bienvenue)' : '') + '\n';
    if (pr) s += 'Parrainage : ' + pr + '\n';
    return s;
  }

  function send(num, txt) {
    var f = new FormData();
    f.append('_subject', 'Commande ' + num + ' — ' + $('nom').value.trim() + ' (' + money(totals().total) + ')');
    f.append('_template', 'box'); f.append('_captcha', 'false');
    if (CFG.cc) f.append('_cc', CFG.cc);
    f.append('Commande', txt);
    return fetch('https://formsubmit.co/ajax/' + CFG.mail, { method: 'POST', body: f, headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (!j || String(j.success) === 'false' && !/activ/i.test(j.message || '')) throw new Error(j && j.message); return j; });
  }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (!validate()) return;
    var btn = $('confirm-btn'); btn.disabled = true; btn.textContent = 'Enregistrement…'; $('send-err').style.display = 'none';
    var num = orderNumber(), txt = orderText(num), t = totals(), L = window.LRloyal;
    send(num, txt).then(function () {
      var s = L.get(); s.tel = $('tel').value.trim(); s.name = $('prenom').value.trim() || s.name; L.set(s);
      var first = s.orders === 0, pr = $('parrain').value.trim();
      if (t.red) L.redeem();
      L.credit(t.st, (first && pr) ? 50 : 0);
      $('c-name').textContent = ($('prenom').value.trim() || $('nom').value.trim().split(' ')[0]);
      $('c-num').textContent = 'n° ' + num;
      $('c-next').textContent = mode() === 'retrait'
        ? 'Nous vous appelons au ' + $('tel').value.trim() + ' dès qu\'elle est prête à être retirée, ' + CFG.addr + ', ' + CFG.city + '. Paiement sur place.'
        : 'Livraison sous ' + CFG.days + ' à l\'adresse indiquée. Vous réglez ' + money(t.total) + ' en espèces au livreur.';
      $('c-sum').innerHTML = sumHTML(t) + '<p class="muted" style="font-size:13px;margin-top:10px">Un récapitulatif a été transmis à la parapharmacie.</p>';
      window.LRcart.write([]);
      $('cart-page').classList.add('hidden'); $('confirm').style.display = 'block';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }).catch(function () {
      btn.disabled = false; btn.textContent = 'Confirmer ma commande';
      $('err-wa').href = 'https://wa.me/' + CFG.wa + '?text=' + encodeURIComponent(txt);
      $('send-err').style.display = 'block';
    });
  });

  window.LRpaintCart();
});
