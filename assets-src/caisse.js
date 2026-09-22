/* Caisse La Rose — saisie boutique, 3 écrans : PIN → client + montant → confirmation. */
document.addEventListener('DOMContentLoaded', function () {
  var W = window.LR_WORKER, $ = function (id) { return document.getElementById(id); };
  var pin = '', cust = null;
  try { pin = localStorage.getItem('larose_pin') || ''; } catch (e) {}
  function show(id) { document.querySelectorAll('.scr').forEach(function (s) { s.classList.toggle('on', s.id === id); }); window.scrollTo(0, 0); }
  function api(path, opts) { return fetch(W + path, opts).then(function (r) { return r.json(); }); }
  function money(n) { return window.LRmoney(n); }
  function tel() { return $('c-tel').value.replace(/\D/g, '').slice(-8); }

  // --- PIN
  var buf = '';
  function paintPin() { $('pin-dots').textContent = '●'.repeat(buf.length) + '○'.repeat(Math.max(0, 4 - buf.length)); }
  document.querySelectorAll('#pad button').forEach(function (b) {
    b.addEventListener('click', function () {
      var k = b.getAttribute('data-k');
      if (k === 'del') buf = buf.slice(0, -1); else if (buf.length < 6) buf += k;
      paintPin();
      if (buf.length >= 4) tryPin(buf);
    });
  });
  function tryPin(p) {
    $('pin-err').textContent = '';
    api('/recent?pin=' + encodeURIComponent(p)).then(function (j) {
      if (Array.isArray(j)) { pin = p; try { localStorage.setItem('larose_pin', p); } catch (e) {} paintRecent(j); show('scr-entry'); $('c-tel').focus(); }
      else if (buf.length >= 6 || j.error === 'pin' && buf.length >= 4 && buf.length < 6) { if (buf.length >= 6 || j.error) { $('pin-err').textContent = 'Code incorrect'; buf = ''; paintPin(); } }
    }).catch(function () { $('pin-err').textContent = 'Connexion impossible'; });
  }
  function paintRecent(list) {
    var today = new Date().toISOString().slice(0, 10);
    var rows = list.filter(function (o) { return o.d.slice(0, 10) === today; }).slice(0, 12);
    $('recent').innerHTML = rows.length ? rows.map(function (o) {
      return '<div><span>' + o.d.slice(11) + ' · ' + (o.name || '') + ' ' + o.tel.slice(-4).padStart(8, '•') + (o.src === 'site' ? ' (site)' : '') + '</span><span>' + (o.redeem ? '−bon · ' : '') + '+' + o.p + '</span></div>';
    }).join('') : '<div class="muted">Aucune saisie aujourd\'hui.</div>';
  }
  $('logout').addEventListener('click', function () { pin = ''; buf = ''; try { localStorage.removeItem('larose_pin'); } catch (e) {} paintPin(); show('scr-pin'); });

  // --- client lookup
  $('c-tel').addEventListener('input', function () {
    var t = tel(); cust = null; $('cust').style.display = 'none'; $('redeem-t').style.display = 'none'; $('c-name-wrap').style.display = 'none';
    if (t.length === 8) api('/balance?tel=' + t).then(function (c) {
      cust = c; paintCust(c);
    });
  });
  function paintCust(c) {
    $('cust').style.display = 'flex';
    $('cust-rose').innerHTML = window.LRroseSVG('cr2'); $('cr2').setAttribute('data-rose', '');
    var isNew = !c.orders && !c.petals;
    $('cust-name').textContent = isNew ? 'Nouvelle cliente ✿' : (c.name || 'Cliente') ;
    $('cust-pts').textContent = isNew ? 'Première visite — cadeau de bienvenue !' : c.petals + ' pétales · ' + c.orders + ' achat' + (c.orders > 1 ? 's' : '');
    $('cust-bon').style.display = c.bons > 0 ? 'inline-block' : 'none';
    $('cust-bon').textContent = c.bons + ' bon' + (c.bons > 1 ? 's' : '') + ' de ' + c.bon + ' DT disponible' + (c.bons > 1 ? 's' : '');
    $('redeem-t').style.display = c.bons > 0 ? 'flex' : 'none'; $('redeem').checked = false; $('redeem-t').classList.remove('on');
    $('c-name-wrap').style.display = isNew || !c.name ? 'block' : 'none';
    // rose remplie selon le solde serveur
    var s = window.LRloyal.get(); s.petals = c.petals; window.LRloyal.set(s);
  }
  $('redeem').addEventListener('change', function () { $('redeem-t').classList.toggle('on', this.checked); });

  // --- save
  $('save').addEventListener('click', function () {
    var t = tel(), a = parseFloat(($('c-amt').value || '').replace(',', '.'));
    $('entry-err').textContent = '';
    if (t.length !== 8) { $('entry-err').textContent = 'Numéro à 8 chiffres.'; $('c-tel').focus(); return; }
    if (!(a >= 0)) { $('entry-err').textContent = 'Montant de l\'achat en dinars.'; $('c-amt').focus(); return; }
    $('save').disabled = true;
    api('/instore', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin: pin, tel: t, name: $('c-name').value.trim(), amount: a, redeem: $('redeem').checked }) })
      .then(function (c) {
        $('save').disabled = false;
        if (c.error) { $('entry-err').textContent = c.error === 'pin' ? 'Code PIN expiré — reconnectez-vous.' : 'Erreur : ' + c.error; return; }
        $('done-n').textContent = '+' + Math.floor(a);
        $('done-t').textContent = (c.name ? c.name + ' a ' : 'Total : ') + c.petals + ' pétales' + (c.bons ? ' · ' + c.bons + ' bon' + (c.bons > 1 ? 's' : '') + ' de ' + c.bon + ' DT à offrir !' : ' · encore ' + (c.step - c.petals % c.step) + ' avant le prochain bon');
        $('done-first').style.display = c.first ? 'block' : 'none';
        var s = window.LRloyal.get(); s.petals = c.petals; window.LRloyal.set(s);
        $('done-rose').innerHTML = window.LRroseSVG('cr3'); $('cr3').setAttribute('data-rose', ''); window.LRloyalRepaint();
        show('scr-done');
        api('/recent?pin=' + encodeURIComponent(pin)).then(function (j) { if (Array.isArray(j)) paintRecent(j); });
      }).catch(function () { $('save').disabled = false; $('entry-err').textContent = 'Connexion impossible. Réessayez.'; });
  });
  $('again').addEventListener('click', function () {
    $('c-tel').value = ''; $('c-amt').value = ''; $('c-name').value = ''; cust = null;
    $('cust').style.display = 'none'; $('redeem-t').style.display = 'none'; $('c-name-wrap').style.display = 'none';
    show('scr-entry'); $('c-tel').focus();
  });

  paintPin();
  if (!W) { $('pin-err').textContent = 'Caisse non configurée (WORKER_URL).'; }
  else if (pin) tryPin(pin);
});
