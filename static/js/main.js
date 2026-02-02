/**
 * Healthy Feet - Sistema de Gestión
 * JavaScript principal con funcionalidades comunes
 */

document.addEventListener('DOMContentLoaded', function() {
    // =========================================================================
    // INICIALIZACIÓN
    // =========================================================================
    
    initSidebar();
    initFlashMessages();
    initForms();
    initGlobalLoader();
    
    // =========================================================================
    // FUNCIONES DE INICIALIZACIÓN
    // =========================================================================
    
    function initSidebar() {
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebar = document.querySelector('.sidebar');
        
        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', function() {
                sidebar.classList.toggle('active');
            });
        }
        
        // Cerrar sidebar al hacer clic fuera en móviles
        document.addEventListener('click', function(event) {
            if (window.innerWidth <= 992 && sidebar && sidebar.classList.contains('active')) {
                if (!sidebar.contains(event.target) && 
                    !sidebarToggle.contains(event.target)) {
                    sidebar.classList.remove('active');
                }
            }
        });
    }
    
    function initFlashMessages() {
        const alerts = document.querySelectorAll('.alert');
        
        alerts.forEach(alert => {
            const closeBtn = alert.querySelector('.alert-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', function() {
                    alert.style.opacity = '0';
                    setTimeout(() => {
                        alert.style.display = 'none';
                    }, 300);
                });
            }
            
            // Auto-remover mensajes después de 5 segundos
            setTimeout(() => {
                if (alert.style.display !== 'none') {
                    alert.style.opacity = '0';
                    setTimeout(() => {
                        alert.style.display = 'none';
                    }, 300);
                }
            }, 5000);
        });
    }
    
    function initForms() {
        // Validación de teléfono
        const phoneInputs = document.querySelectorAll('input[type="tel"]');
        phoneInputs.forEach(input => {
            input.addEventListener('input', function() {
                this.value = this.value.replace(/\D/g, '').slice(0, 10);
            });
        });
        
        // Validación de contraseña
        const passwordInputs = document.querySelectorAll('input[type="password"]');
        passwordInputs.forEach(input => {
            if (input.hasAttribute('minlength')) {
                input.addEventListener('input', function() {
                    const minLength = parseInt(this.getAttribute('minlength'));
                    if (this.value.length < minLength) {
                        this.setCustomValidity(`Mínimo ${minLength} caracteres`);
                    } else {
                        this.setCustomValidity('');
                    }
                });
            }
        });
        
        // Confirmación antes de acciones importantes
        const dangerousButtons = document.querySelectorAll('.btn-danger[type=submit], .btn-finalizar:not(.no-confirm)');
        dangerousButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (this.classList.contains('btn-finalizar') && 
                    !this.classList.contains('no-confirm')) {
                    if (!confirm('¿Estás seguro de realizar esta acción?')) {
                        e.preventDefault();
                    }
                }
            });
        });
    }
    
    function initGlobalLoader() {
        const loader = document.getElementById('global-loader');
        
        if (loader) {
            // Ocultar loader después de cargar la página
            window.addEventListener('load', function() {
                setTimeout(() => {
                    loader.classList.add('hidden');
                }, 500);
            });
            
            // Mostrar loader en envíos de formularios
            const forms = document.querySelectorAll('form');
            forms.forEach(form => {
                form.addEventListener('submit', function() {
                    if (!this.classList.contains('no-loader')) {
                        loader.classList.remove('hidden');
                    }
                });
            });
            
            // Mostrar loader en clics de botones importantes
            const actionButtons = document.querySelectorAll('a.btn, button[type="submit"]');
            actionButtons.forEach(button => {
                button.addEventListener('click', function() {
                    if (!this.classList.contains('no-loader')) {
                        loader.classList.remove('hidden');
                    }
                });
            });
        }
    }
    
    // =========================================================================
    // FUNCIONES UTILITARIAS
    // =========================================================================
    
    window.toggleElement = function(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.toggle('d-none');
        }
    };
    
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(() => {
            alert('Copiado al portapapeles');
        }).catch(err => {
            console.error('Error al copiar: ', err);
        });
    };
    
    window.formatCurrency = function(amount) {
        return new Intl.NumberFormat('es-MX', {
            style: 'currency',
            currency: 'MXN'
        }).format(amount);
    };
    
    window.formatDate = function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('es-MX', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    };
    
    // =========================================================================
    // MANEJO DE ERRORES
    // =========================================================================
    
    window.addEventListener('error', function(e) {
        console.error('Error capturado:', e.error);
        const loader = document.getElementById('global-loader');
        if (loader) {
            loader.classList.add('hidden');
        }
    });
    
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Promise rechazada:', e.reason);
        const loader = document.getElementById('global-loader');
        if (loader) {
            loader.classList.add('hidden');
        }
    });
});