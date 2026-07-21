/* ==========================================================================
   progression_common.js
   Shared helpers for the Progression Hub, Levels, and Achievements admin
   pages. Load this BEFORE each page's own script.
   ========================================================================== */

/**
 * Set the value of a form field by id. No-ops safely if the field
 * isn't on the page (e.g. when a page-specific script runs on the
 * Hub page, which contains multiple forms at once).
 */
function pgSetValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
}

/**
 * Set the checked state of a checkbox field by id.
 */
function pgSetChecked(id, checked) {
    const el = document.getElementById(id);
    if (el) el.checked = !!checked;
}

/**
 * Set the visible text of an element by id (e.g. a modal title).
 */
function pgSetText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

/**
 * Open a Bootstrap modal by id.
 */
function pgOpenModal(modalId) {
    const modalEl = document.getElementById(modalId);
    if (!modalEl) return;
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}