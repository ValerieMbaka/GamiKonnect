document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('profileCompletionModal');
    
    // Check if profile is already completed
    const profileCompleted = localStorage.getItem('profileCompleted') === 'true';
    
    if (profileCompleted && modal) {
        modal.classList.remove('show', 'mandatory');
        modal.style.display = 'none';
    }
    
    if (modal && modal.classList.contains('show')) {
        modal.classList.add('mandatory');
    }
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal && modal.classList.contains('mandatory')) {
            e.stopPropagation();
        }
    });
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('mandatory')) {
            e.preventDefault();
        }
    });
    
    window.clearProfileCompletion = function() {
        localStorage.removeItem('profileCompleted');
        localStorage.removeItem('updatedProfile');
    };
});