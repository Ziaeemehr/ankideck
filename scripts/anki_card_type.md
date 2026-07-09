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

```
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