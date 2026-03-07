document.addEventListener('DOMContentLoaded', () => {
    const animatedSections = document.querySelectorAll('.anim-fade-in-up');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
            }
        });
    }, { threshold: 0.2 });

    animatedSections.forEach(section => observer.observe(section));
});

