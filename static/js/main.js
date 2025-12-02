// main.js
document.addEventListener('DOMContentLoaded', function() {
// puedes agregar efectos o clicks sobre las tarjetas
document.querySelectorAll('.card-category').forEach(card => {
    card.addEventListener('click', () => {
    // efecto pequeño
    card.classList.add('border-success');
    setTimeout(()=> card.classList.remove('border-success'), 600);
    });
});
});
