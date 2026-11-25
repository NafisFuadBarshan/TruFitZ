// quantity steppers on product page
document.querySelectorAll('.pd .qty button').forEach(b => b.addEventListener('click', () => {
  const i = b.parentElement.querySelector('input');
  i.value = Math.min(10, Math.max(1, (+i.value || 1) + (+b.dataset.d)));
}));
// scroll reveal
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: .1 });
document.querySelectorAll('.reveal').forEach(el => io.observe(el));
// auto-dismiss flash messages
setTimeout(() => document.querySelectorAll('.flash').forEach(f => f.remove()), 5000);
