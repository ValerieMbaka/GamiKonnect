document.addEventListener('DOMContentLoaded', function() {
    console.log('Public Profile JavaScript loaded');
    
    initializeGameImages();
    initializeAchievementsList();
   
    function getGameImage(gameName) {
        const gameNameLower = gameName.toLowerCase();
        
        // FPS Games
        if (gameNameLower.includes('valorant') || gameNameLower.includes('csgo') || gameNameLower.includes('cs:go') || gameNameLower.includes('counter-strike')) {
            return '/static/core/images/cod.jpeg';
        }
        if (gameNameLower.includes('cod') || gameNameLower.includes('call of duty') || gameNameLower.includes('warzone')) {
            return '/static/core/images/codwarzone.jpeg';
        }
        if (gameNameLower.includes('cod mobile') || gameNameLower.includes('call of duty mobile')) {
            return '/static/core/images/codmobile.jpeg';
        }
        if (gameNameLower.includes('black ops')) {
            return '/static/core/images/codblackops.jpeg';
        }
        
        // Sports Games
        if (gameNameLower.includes('fifa') || gameNameLower.includes('football') || gameNameLower.includes('soccer')) {
            return '/static/core/images/fc.jpeg';
        }
        if (gameNameLower.includes('pes') || gameNameLower.includes('efootball') || gameNameLower.includes('pro evolution soccer')) {
            return '/static/core/images/pes.jpeg';
        }
        
        // Racing Games
        if (gameNameLower.includes('nfs') || gameNameLower.includes('need for speed')) {
            return '/static/core/images/nfs.jpeg';
        }
        if (gameNameLower.includes('racing') || gameNameLower.includes('asphalt')) {
            return '/static/core/images/racing.jpeg';
        }
        if (gameNameLower.includes('asphalt legends')) {
            return '/static/core/images/asphaltlegends.jpeg';
        }
        
        // Fighting Games
        if (gameNameLower.includes('tekken') || gameNameLower.includes('fighting')) {
            return '/static/core/images/tekken.jpeg';
        }
        
        // Battle Royale Games
        if (gameNameLower.includes('pubg') || gameNameLower.includes('playerunknown')) {
            return '/static/core/images/pubg.jpeg';
        }
        if (gameNameLower.includes('fortnite')) {
            return '/static/core/images/fortnite.jpeg';
        }
        if (gameNameLower.includes('freefire') || gameNameLower.includes('free fire')) {
            return '/static/core/images/freefire.jpeg';
        }
        
        // Mobile Games
        if (gameNameLower.includes('roblox')) {
            return '/static/core/images/roblox.jpeg';
        }
        if (gameNameLower.includes('dream league') || gameNameLower.includes('dream league soccer')) {
            return '/static/core/images/fc.jpeg';
        }
        
        // Action Games
        if (gameNameLower.includes('action') || gameNameLower.includes('adventure')) {
            return '/static/core/images/actiongame.jpeg';
        }
        
        // Default fallback
        return '/static/core/images/gamepad.jpeg';
    }
    
    // Initialize game images
    function initializeGameImages() {
        // Initialize game banner images
        const gameBanners = document.querySelectorAll('.game-banner');
        gameBanners.forEach(img => {
            const gameName = img.getAttribute('data-game');
            if (gameName) {
                img.src = getGameImage(gameName);
            }
        });
        
        // Initialize game card images
        const gameImages = document.querySelectorAll('.game-image');
        gameImages.forEach(img => {
            const gameName = img.getAttribute('data-game');
            if (gameName) {
                img.src = getGameImage(gameName);
            }
        });
        
        // Initialize activity game images
        const activityGameImages = document.querySelectorAll('.activity-game-image');
        activityGameImages.forEach(img => {
            const gameNames = img.getAttribute('data-game');
            if (gameNames) {
                // Get the first game from the comma-separated list
                const firstGame = gameNames.split(',')[0].trim();
                img.src = getGameImage(firstGame);
            }
        });
    }
   
    function initializeAchievementsList() {
        const achievementCards = document.querySelectorAll('.achievement-card');
        
        achievementCards.forEach(card => {
            card.addEventListener('click', function() {
                // Add click animation
                this.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
                
                const achievementTitle = this.querySelector('h4').textContent;
                console.log('Achievement clicked:', achievementTitle);
                
                showToast(`Achievement: ${achievementTitle}`, 'info');
            });
        });
    }
    
    // Show toast notification
    function showToast(message, type = 'info') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            console.log('Toast:', message);
        }
    }
    
    const achievementItems = document.querySelectorAll('.achievement-item');
    achievementItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px) scale(1.02)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
    
    const activityItems = document.querySelectorAll('.activity-item');
    activityItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(4px)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
    
    const buttons = document.querySelectorAll('.btn-follow, .btn-message, .btn-icon');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (this.id === 'followBtn') return;
            
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
    
    // Add loading animation for images
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        img.addEventListener('load', function() {
            this.style.opacity = '1';
        });
        
        img.addEventListener('error', function() {
            console.log('Image failed to load:', this.src);
            // Set fallback image
            this.src = '/static/core/images/gamepad.jpeg';
        });
    });
    
    // Initialize tooltips
    function initializeTooltips() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', function() {
                const tooltip = this.getAttribute('data-tooltip');
                showTooltip(this, tooltip);
            });
            
            element.addEventListener('mouseleave', function() {
                hideTooltip();
            });
        });
    }
    
    function showTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = text;
        tooltip.style.cssText = `
            position: absolute;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            z-index: 1000;
            pointer-events: none;
            white-space: nowrap;
        `;
        
        document.body.appendChild(tooltip);
        
        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
        
        element._tooltip = tooltip;
    }
    
    function hideTooltip() {
        const tooltips = document.querySelectorAll('.custom-tooltip');
        tooltips.forEach(tooltip => tooltip.remove());
    }
    
    initializeTooltips();
    
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add intersection observer for animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    const animatedElements = document.querySelectorAll('.profile-card, .featured-game-card, .achievement-item');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
    
    console.log('Public Profile JavaScript initialized successfully');
});
