// main.js
document.addEventListener('DOMContentLoaded', function() {
    // Efectos en las tarjetas de categorías
    document.querySelectorAll('.card-category').forEach(card => {
        card.addEventListener('click', () => {
            // efecto pequeño
            card.classList.add('border-success');
            setTimeout(()=> card.classList.remove('border-success'), 600);
        });
    });

    // Funcionalidad del navbar: estados activos
    function setActiveNavItem() {
        const currentPath = window.location.pathname;
        
        // Remover todas las clases active
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            link.removeAttribute('aria-current');
        });

        // Establecer activo según la ruta actual
        if (currentPath === '/' || currentPath === '/index') {
            const navIndex = document.getElementById('nav-index');
            if (navIndex) {
                navIndex.classList.add('active');
                navIndex.setAttribute('aria-current', 'page');
            }
        } else if (currentPath === '/admin' || currentPath === '/admin/dashboard') {
            const navAdmin = document.getElementById('nav-admin');
            if (navAdmin) {
                navAdmin.classList.add('active');
            }
        }
    }

    // Ejecutar al cargar la página
    setActiveNavItem();
});
