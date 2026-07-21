/* ==========================================================================
   admin_level_list.js
   Level create/edit modal handlers. Depends on progression_common.js.
   ========================================================================== */

const LEVEL_DEFAULT_COLOR = '#35A8F0';

function resetLevelForm() {
    pgSetValue('level_id', '');
    pgSetValue('level_name', '');
    pgSetValue('level_points', '');
    pgSetValue('level_order', '');
    pgSetValue('level_color', LEVEL_DEFAULT_COLOR);
    pgSetText('levelModalLabel', 'Add New Level');
}

function editLevel(id, name, points, order, colorHex) {
    pgSetValue('level_id', id);
    pgSetValue('level_name', name);
    pgSetValue('level_points', points);
    pgSetValue('level_order', order);
    pgSetValue('level_color', colorHex || LEVEL_DEFAULT_COLOR);
    pgSetText('levelModalLabel', 'Edit Level');
    pgOpenModal('levelModal');
}