// djbaozi Admin JS
document.addEventListener('DOMContentLoaded', function() {
    // Confirm destructive actions
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) e.preventDefault();
        });
    });

    // Auto-dismiss alerts after 5s
    document.querySelectorAll('.alert-dismissible').forEach(el => {
        setTimeout(() => {
            el.classList.add('fade');
            setTimeout(() => el.remove(), 300);
        }, 5000);
    });
});
