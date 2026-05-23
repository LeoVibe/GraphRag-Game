export function makeDraggable(el, payload) {
  el.draggable = true;
  el.addEventListener('dragstart', e => {
    e.dataTransfer.setData('text/plain', JSON.stringify(payload));
    el.classList.add('is-dragging');
  });
  el.addEventListener('dragend', () => el.classList.remove('is-dragging'));
}
export function makeDropZone(el, onDrop) {
  el.addEventListener('dragover', e => { e.preventDefault(); el.classList.add('is-drop-target'); });
  el.addEventListener('dragleave', () => el.classList.remove('is-drop-target'));
  el.addEventListener('drop', e => {
    e.preventDefault();
    el.classList.remove('is-drop-target');
    try {
      const payload = JSON.parse(e.dataTransfer.getData('text/plain'));
      onDrop(payload, el);
    } catch {}
  });
}
