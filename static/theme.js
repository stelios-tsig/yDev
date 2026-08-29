// Εναλλαγή θέματος: κανονικό <-> νυχτερινό (Matrix).
// Η επιλογή αποθηκεύεται στο localStorage και εφαρμόζεται πριν το render
// (το script φορτώνεται στο <head>) ώστε να μην υπάρχει αναλαμπή.
(function () {
    var KEY = "ydev-theme";

    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) {}
    if (saved === "matrix") {
        document.documentElement.setAttribute("data-theme", "matrix");
    }

    var btn = null;

    function isMatrix() {
        return document.documentElement.getAttribute("data-theme") === "matrix";
    }

    function updateLabel() {
        if (btn) {
            btn.textContent = isMatrix() ? "☀ Κανονικό" : "🌙 Νυχτερινό";
        }
    }

    function apply(theme) {
        if (theme === "matrix") {
            document.documentElement.setAttribute("data-theme", "matrix");
        } else {
            document.documentElement.removeAttribute("data-theme");
        }
        try { localStorage.setItem(KEY, theme); } catch (e) {}
        updateLabel();
    }

    document.addEventListener("DOMContentLoaded", function () {
        btn = document.createElement("button");
        btn.id = "theme-toggle";
        btn.type = "button";
        updateLabel();
        btn.addEventListener("click", function () {
            apply(isMatrix() ? "light" : "matrix");
        });
        document.body.appendChild(btn);
    });
})();
