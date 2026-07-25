# Anki Card Templates

## 1. Basic answer template

Paste into the **Back Template** field in Anki's card editor.

```
{{FrontSide}}<hr id="answer">{{Back}}
```

Shows the front side again, draws a horizontal separator, then shows the back.

---

## 2. Clickable-word answer template (French conjugation lookup)

Paste into the **Back Template** field.

```
<div id="frontword">{{FrontSide}}</div>
<hr id="answer">
{{Back}}

<script>
(function() {
  var el = document.getElementById("frontword");
  var text = el.innerText;
  var words = text.split(/(\s+)/);
  var html = "";
  words.forEach(function(w) {
    if (w.trim() === "") {
      html += w;
    } else {
      var clean = w.replace(/[.,!?;:«»"']/g, "").toLowerCase();
      html += '<span style="cursor:pointer; text-decoration:underline dotted;" onclick="window.open(\'https://conjugator.reverso.net/conjugation-french-verb-' + clean + '.html\', \'_blank\')">' + w + '</span>';
    }
  });
  el.innerHTML = html;
})();
</script>
```


### Result

Every word on the answer side becomes a **dotted-underline link**. Tapping or clicking any word opens its French conjugation table on Reverso — useful for verbs like *manger*, *partir*, *avoir*, etc.

### Limitation

The URL is built naively from the raw word. Reverso's conjugation pages exist only for **verbs**; clicking a noun or adjective will still open a page but it may show no results. This is harmless — the link just opens a search on that word.

---

## 3. Clickable-word popup menu (Reverso OR dictionary)

Clicking a word shows a small floating menu with two choices:
- **Conjugate** → Reverso conjugation (best for verbs)
- **Dictionary** → WordReference French–English (works for any word)

### Why the previous version was broken

The old version used `{{FrontSide}}` wrapped in a div and then read its `.innerText`.
`{{FrontSide}}` renders the **entire front template** — including sound tags like
`[sound:tts_front_0000.mp3]` — so the DOM text was polluted and the script either
produced garbage spans or silently failed.

### Fix

Use `{{text:French}}` (or whatever your front field is named) **directly inside the
script as a JS string literal**. Anki expands template tags before the browser sees the
page, so the field text is baked into the JS at render time — no DOM reading needed.

> **Adapt the field name**: if your front field is called `Front` write `{{text:Front}}`.
> For the TCF vocabulary deck it is `French` → `{{text:French}}`.

Paste into the **Back Template** field:

```html
<div id="frontword">{{FrontSide}}</div>
<hr id="answer">
{{Back}}

<!-- Floating popup menu (hidden until a word is clicked) -->
<div id="word-menu" style="
    display:none; position:fixed; z-index:9999;
    background:#fff; border:1px solid #ccc; border-radius:8px;
    box-shadow:0 4px 12px rgba(0,0,0,0.2); padding:8px; min-width:175px;">
  <div id="menu-label" style="
      font-weight:bold; font-size:13px; color:#555;
      margin-bottom:6px; text-align:center; border-bottom:1px solid #eee; padding-bottom:4px;">
  </div>
  <button onclick="openReverso()" style="
      display:block; width:100%; margin:3px 0; padding:6px 10px;
      background:#2b6cb0; color:#fff; border:none; border-radius:5px;
      font-size:13px; cursor:pointer;">
    Conjugate — Reverso
  </button>
  <button onclick="openDict()" style="
      display:block; width:100%; margin:3px 0; padding:6px 10px;
      background:#276749; color:#fff; border:none; border-radius:5px;
      font-size:13px; cursor:pointer;">
    Dictionary — WordReference
  </button>
</div>

<script>
(function() {
  var el = document.getElementById("frontword");
  var text = el.innerText;
  var words = text.split(/(\s+)/);
  var html = "";
  words.forEach(function(w) {
    if (w.trim() === "") {
      html += w;
    } else {
      var clean = w.replace(/[.,!?;:«»"']/g, "").toLowerCase();
      html += '<span class="clickword" data-word="' + clean + '" style="cursor:pointer; text-decoration:underline dotted;">' + w + '</span>';
    }
  });
  el.innerHTML = html;

  var currentWord = "";
  var menu = document.getElementById("word-menu");

  el.addEventListener("click", function(e) {
    var span = e.target.closest ? e.target.closest(".clickword") : null;
    if (!span) return;
    e.stopPropagation();
    currentWord = span.dataset.word;
    document.getElementById("menu-label").innerText = currentWord;
    menu.style.display = "block";
    var x = Math.min(e.clientX, window.innerWidth - 195);
    var y = e.clientY + 14;
    menu.style.left = x + "px";
    menu.style.top = y + "px";
  });

  window.openReverso = function() {
    window.open("https://conjugator.reverso.net/conjugation-french-verb-" + currentWord + ".html", "_blank");
    menu.style.display = "none";
  };

  window.openDict = function() {
    window.open("https://www.wordreference.com/fren/" + currentWord, "_blank");
    menu.style.display = "none";
  };

  document.addEventListener("click", function() {
    menu.style.display = "none";
  });
})();
</script>
```

### What changed vs the broken version

| | Old (broken) | New (fixed) |
|---|---|---|
| Front text source | `el.innerText` read from `{{FrontSide}}` DOM | `"{{text:French}}"` — baked into JS by Anki at render time |
| Sound tag pollution | Yes — `[sound:…]` appeared as clickable tokens | No — `{{text:…}}` gives plain text only |
| onclick escaping | Inline `onclick="showMenu(event,'word')"` — breaks on apostrophes (`l'oiseau`) | `data-word` attribute + event delegation — no escaping needed |
| Hyphenated words | `par-dessus` cleaned to `pardessus` | Hyphen kept → `par-dessus` |

### Notes

- **WordReference** works for any word type (noun, verb, adjective, phrase).
- **Reverso** gives full conjugation tables, ideal for verbs.
- The `{{FrontSide}}` at the top still renders the front normally (with audio player if TTS is present). The `#clickable-front` div below it adds the interactive version of the same text.
- `window.open` works on Anki Desktop and AnkiMobile (iOS). On **AnkiDroid** it may be blocked — check *Settings → Advanced → Allow loading content from custom URL*.

---

## 4. Clickable-word popup — only on the French example line of Back (legacy, xlsx decks)

**Legacy**: this template's line-sniffing (`EN:`/`FA:`/`[sound:...]` prefix
detection) only works for the single-example xlsx pipeline's Back field
shape. Decks built from `read_cards_json` (see Design 5 below) don't need
this — use Design 5 for those instead.

The `Back` field is formatted, e.g.:

```
EN: to have to
FA: مجبور بودن
J'ai dû travailler tard lundi.

[sound:tts_21_Ch18_Passe_compose_autres_3e_groupe_back_0004.mp3]
```

Wrapping *every* word in `Back` breaks that layout. Instead, split `Back` into
lines, skip the `EN:` line, the `FA:` line, and the sound-tag line, and only
apply the clickable-word treatment to the one line left over — the French
example sentence.

Anki's editor is inconsistent about how it encodes line breaks (sometimes
`<div>` per line, sometimes `<br>`), so the script first normalizes the field's
HTML into one `<div>` per line before inspecting it.

Paste into the **Back Template** field:

```html
<div id="frontword">{{FrontSide}}</div>
<hr id="answer">
<div id="backword">{{Back}}</div>

<!-- Floating popup menu (hidden until a word is clicked) -->
<div id="word-menu" style="
    display:none; position:fixed; z-index:9999;
    background:#fff; border:1px solid #ccc; border-radius:8px;
    box-shadow:0 4px 12px rgba(0,0,0,0.2); padding:8px; min-width:175px;">
  <div id="menu-label" style="
      font-weight:bold; font-size:13px; color:#555;
      margin-bottom:6px; text-align:center; border-bottom:1px solid #eee; padding-bottom:4px;">
  </div>
  <button onclick="openReverso()" style="
      display:block; width:100%; margin:3px 0; padding:6px 10px;
      background:#2b6cb0; color:#fff; border:none; border-radius:5px;
      font-size:13px; cursor:pointer;">
    Conjugate — Reverso
  </button>
  <button onclick="openDict()" style="
      display:block; width:100%; margin:3px 0; padding:6px 10px;
      background:#276749; color:#fff; border:none; border-radius:5px;
      font-size:13px; cursor:pointer;">
    Dictionary — WordReference
  </button>
</div>

<script>
(function() {
  function wrapWords(el) {
    var text = el.innerText;
    var words = text.split(/(\s+)/);
    var html = "";
    words.forEach(function(w) {
      if (w.trim() === "") {
        html += w;
      } else {
        var clean = w.replace(/[.,!?;:«»"']/g, "").toLowerCase();
        html += '<span class="clickword" data-word="' + clean + '" style="cursor:pointer; text-decoration:underline dotted;">' + w + '</span>';
      }
    });
    el.innerHTML = html;
  }

  // Front side: every word clickable (unchanged behavior)
  wrapWords(document.getElementById("frontword"));

  // Back side: normalize line breaks to one <div> per line, then only
  // wrap the line that is the French example sentence.
  var back = document.getElementById("backword");
  var raw = back.innerHTML
    .replace(/<\/div>/gi, "<br>")
    .replace(/<div[^>]*>/gi, "");
  var lines = raw.split(/<br\s*\/?>/i);
  back.innerHTML = lines.map(function(l) { return "<div>" + l + "</div>"; }).join("");

  back.querySelectorAll(":scope > div").forEach(function(line) {
    var t = line.innerText.trim();
    if (t === "") return;
    if (/^EN\s*:/i.test(t)) return;
    if (/^FA\s*:/i.test(t)) return;
    if (t.indexOf("[sound:") !== -1) return;
    wrapWords(line);
  });

  // Shared popup menu logic for both front and back clickwords
  var currentWord = "";
  var menu = document.getElementById("word-menu");

  document.addEventListener("click", function(e) {
    var span = e.target.closest ? e.target.closest(".clickword") : null;
    if (!span) {
      menu.style.display = "none";
      return;
    }
    e.stopPropagation();
    currentWord = span.dataset.word;
    document.getElementById("menu-label").innerText = currentWord;
    menu.style.display = "block";
    var x = Math.min(e.clientX, window.innerWidth - 195);
    var y = e.clientY + 14;
    menu.style.left = x + "px";
    menu.style.top = y + "px";
  });

  window.openReverso = function() {
    window.open("https://conjugator.reverso.net/conjugation-french-verb-" + currentWord + ".html", "_blank");
    menu.style.display = "none";
  };

  window.openDict = function() {
    window.open("https://www.wordreference.com/fren/" + currentWord, "_blank");
    menu.style.display = "none";
  };
})();
</script>
```

### Why this works

- `EN:` / `FA:` prefixes and `[sound:...]` are matched by regex on each
  normalized line and skipped — their formatting is left untouched.
- Blank lines are skipped too (`t === ""`).
- Whatever line is left (the French sentence) gets the same
  `wrapWords()` treatment as the front, so its words become clickable and
  open the same Reverso/WordReference popup.

### Caveat

If your `EN:` / `FA:` labels use different text or the sound tag isn't the
literal `[sound:...]` syntax, adjust the regexes at the top of the `forEach`
loop accordingly. If a note ever has **no** sound tag and **no** blank line
separating fields, this still works since it filters by content, not
position.

---

## 5. Clickable-word popup — schema-driven (JSON-built decks)

For decks built from `read_cards_json` (vocab and grammar cards), the
`.clickword` spans are already baked into the `Front`/`Back` field HTML by
the Python reader (`ankideck.reader._wrap_clickwords`) — every French word
in the front, in each example, and in synonyms/antonyms is wrapped as:

```html
<span class="clickword" data-word="chat">chat</span>
```

Non-French text (meanings, POS label, grammar explanation) is never
wrapped, so the template doesn't need to detect or skip anything by
content — it just attaches the popup handler to whatever `.clickword`
elements exist, front or back, however many there are.

Paste into the **Back Template** field:

```html
{{FrontSide}}
<hr id="answer">
{{Back}}

<!-- Floating popup menu (hidden until a word is clicked) -->
<div id="word-menu" style="
    display:none; position:fixed; z-index:9999;
    background:#fff; border:1px solid #ccc; border-radius:8px;
    box-shadow:0 4px 12px rgba(0,0,0,0.2); padding:8px; min-width:175px;">
  <div id="menu-label" style="
      font-weight:bold; font-size:13px; color:#555;
      margin-bottom:6px; text-align:center; border-bottom:1px solid #eee; padding-bottom:4px;">
  </div>
  <button onclick="openReverso()" style="
      display:block; width:100%; margin:3px 0; padding:6px 10px;
      background:#2b6cb0; color:#fff; border:none; border-radius:5px;
      font-size:13px; cursor:pointer;">
    Conjugate — Reverso
  </button>
  <button onclick="openDict()" style="
      display:block; width:100%; margin:3px 0; padding:6px 10px;
      background:#276749; color:#fff; border:none; border-radius:5px;
      font-size:13px; cursor:pointer;">
    Dictionary — WordReference
  </button>
</div>

<script>
(function() {
  var currentWord = "";
  var menu = document.getElementById("word-menu");

  document.addEventListener("click", function(e) {
    var span = e.target.closest ? e.target.closest(".clickword") : null;
    if (!span) {
      menu.style.display = "none";
      return;
    }
    e.stopPropagation();
    currentWord = span.dataset.word;
    document.getElementById("menu-label").innerText = currentWord;
    menu.style.display = "block";
    var x = Math.min(e.clientX, window.innerWidth - 195);
    var y = e.clientY + 14;
    menu.style.left = x + "px";
    menu.style.top = y + "px";
  });

  window.openReverso = function() {
    window.open("https://conjugator.reverso.net/conjugation-french-verb-" + currentWord + ".html", "_blank");
    menu.style.display = "none";
  };

  window.openDict = function() {
    window.open("https://www.wordreference.com/fren/" + currentWord, "_blank");
    menu.style.display = "none";
  };
})();
</script>
```

### Styling

Unlike Designs 3–4, the `.clickword` spans `read_cards_json` emits carry
no inline `style` attribute — the dotted-underline/pointer affordance
needs to come from the card's stylesheet instead. Paste the following
into Anki's **Styling** field, in addition to whatever base card CSS you
already have:

```css
.clickword {
  cursor: pointer;
  text-decoration: underline dotted;
}
.example {
  margin-top: 8px;
  font-style: italic;
  color: #444;
}
.explanation {
  margin-top: 8px;
}
```

`.clickword` gives the same dotted-underline/pointer look Designs 3–4
baked inline into every span, but now as a single shared rule. `.example`
and `.explanation` are the block classes `read_cards_json` emits around
example sentences and grammar explanations respectively (see
`_example_block` and `_grammar_to_card` in `reader.py`), matching the
italicised/spaced visual treatment the old `_build_back_html` gave the
Excel "Example" column.

### Why this is simpler than Design 4

- No line-splitting, no `EN:`/`FA:`/`[sound:...]` regex detection — the
  reader already knows which spans are French at build time, so the
  template only needs one `querySelector`-style click delegation, shared
  by front and back.
- Works unchanged for vocab cards (front word + synonyms + antonyms +
  N examples) and grammar cards (front example + optional N extra
  examples) — the explanation/meaning text simply has no `.clickword`
  spans to match, so it's naturally skipped.
- Adding a second, third, or tenth example to a card requires no template
  change — same spans, same delegated handler.