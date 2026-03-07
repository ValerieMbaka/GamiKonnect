function getRandomLastPlayed() {
    const options = ['Today', 'Yesterday', '2d ago', '3d ago', '1w ago', '2w ago', '1m ago'];
    return options[Math.floor(Math.random() * options.length)];
}

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

// Update user profile
function updateUserProfileUI(data) {
    console.log('Updating user profile UI with data:', data);
    
    if (data.username) {
        const usernameElements = document.querySelectorAll('.profile-name');
        usernameElements.forEach(element => {
            element.textContent = data.username;
        });
    }
    
    if (data.bio) {
        const bioElements = document.querySelectorAll('.profile-title');
        bioElements.forEach(element => {
            element.textContent = data.bio;
        });
    }
    
    if (data.location) {
        const locationElements = document.querySelectorAll('.profile-location span');
        locationElements.forEach(element => {
            element.textContent = data.location;
        });
    }
    
    const gamesTabContent = document.querySelector('#games .game-carousel');
    if (gamesTabContent && data.games && data.games.length > 0) {
        gamesTabContent.innerHTML = data.games.map(game => `
            <div class="game-card">
                <div class="game-status">Active</div>
                <div class="platform-badges">
                    ${data.platforms ? data.platforms.slice(0, 3).map(platform => 
                        `<span class="platform-badge">${platform.toUpperCase()}</span>`
                    ).join('') : '<span class="platform-badge">PC</span>'}
                </div>
                <img src="${getGameImage(game)}" alt="${game}">
                <div class="game-info">
                    <h4>${game}</h4>
                    <div class="game-stats">
                        <div class="stat-item hours" title="Total hours played">
                            <span class="stat-value">${Math.floor(Math.random() * 200) + 50}h</span>
                            <span class="stat-label">Hours</span>
                        </div>
                        <div class="stat-item win-rate" title="Win rate percentage">
                            <span class="stat-value">${Math.floor(Math.random() * 30) + 70}%</span>
                            <span class="stat-label">Win Rate</span>
                        </div>
                        <div class="stat-item achievements" title="Achievements unlocked">
                            <span class="stat-value">${Math.floor(Math.random() * 20) + 5}</span>
                            <span class="stat-label">Achievements</span>
                        </div>
                        <div class="stat-item last-played" title="Last time played">
                            <span class="stat-value">${getRandomLastPlayed()}</span>
                            <span class="stat-label">Last Played</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Update empty states
    const emptyStates = document.querySelectorAll('.empty-state');
    emptyStates.forEach(emptyState => {
        if (emptyState.textContent.includes('No games added yet') && data.games && data.games.length > 0) {
            emptyState.style.display = 'none';
        }
    });
}

// Check for updated profile data on page load
document.addEventListener('DOMContentLoaded', function() {
    const updatedProfile = localStorage.getItem('updatedProfile');
    if (updatedProfile) {
        updateUserProfileUI(JSON.parse(updatedProfile));
        localStorage.removeItem('updatedProfile');
    }
    
    // Check if profile is completed and hide modal if needed
    const profileCompleted = localStorage.getItem('profileCompleted');
    const profileCompletionModal = document.getElementById('profileCompletionModal');
    if (profileCompleted === 'true' && profileCompletionModal) {
        profileCompletionModal.classList.remove('show');
    }
    
    // Handle profile completion modal
    if (profileCompletionModal) {
        // Close modal when clicking outside
        profileCompletionModal.addEventListener('click', function(e) {
            if (e.target === profileCompletionModal) {
                profileCompletionModal.classList.remove('show');
            }
        });
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && profileCompletionModal.classList.contains('show')) {
                profileCompletionModal.classList.remove('show');
            }
        });
    }
    
    // Initialize dashboard tabs
    const dashboardTabs = document.querySelectorAll('.profile-tab');
    console.log('Found dashboard tabs:', dashboardTabs.length);
    
    if (dashboardTabs.length > 0) {
        dashboardTabs.forEach(tab => {
            tab.style.cursor = 'pointer';
            
            tab.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Tab clicked:', this.getAttribute('data-tab'));
                
                // Remove active class from all tabs
                dashboardTabs.forEach(t => t.classList.remove('active'));
                
                // Add active class to clicked tab
                this.classList.add('active');
                
                // Hide all tab contents
                document.querySelectorAll('.profile-tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                
                // Show the corresponding content
                const tabId = this.getAttribute('data-tab');
                if (tabId) {
                    const targetContent = document.getElementById(tabId);
                    if (targetContent) {
                        targetContent.classList.add('active');
                        console.log('Activated tab content:', tabId);
                    } else {
                        console.log('Tab content not found:', tabId);
                    }
                }
            });
        });
    } else {
        console.log('No dashboard tabs found!');
    }

    // Dashboard-specific animations
    const statCards = document.querySelectorAll('.stat-item-horizontal');
    statCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-5px)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });
    });
    
    function initCountdownTimers() {
        const countdowns = document.querySelectorAll('.countdown-timer');
    }

    initCountdownTimers();
    
    // Initialize game images
    function initializeGameImages() {
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
                // Get the first game
                const firstGame = gameNames.split(',')[0].trim();
                img.src = getGameImage(firstGame);
            }
        });
    }
    
    // Initialize game images on page load
    initializeGameImages();
    
    // Initialize competition filters with multiple attempts
    function attemptInitializeFilters() {
        console.log('Attempting to initialize competition filters...');
        const filterButtons = document.querySelectorAll('.competition-filters .filter-btn');
        if (filterButtons.length > 0) {
            console.log('Filter buttons found, initializing...');
            initializeCompetitionFilters();
        } else {
            console.log('No filter buttons found, retrying in 200ms...');
            setTimeout(attemptInitializeFilters, 200);
        }
    }
    
    // Start initialization attempts
    setTimeout(attemptInitializeFilters, 100);
    
    // Avatar upload
    const avatarUpload = document.getElementById('avatarUpload');
    if (avatarUpload) {
        avatarUpload.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const formData = new FormData();
                formData.append('profile_picture', file);
                formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
                
                fetch('/users/complete-profile/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateUserProfileUI(data);
                        // Show success message
                        if (typeof showToast === 'function') {
                            showToast('Avatar updated successfully!', 'success');
                        }
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (typeof showToast === 'function') {
                        showToast('Error updating avatar. Please try again.', 'error');
                    }
                });
            }
        });
    }
    
    // Function to initialize competition filters
    function initializeCompetitionFilters() {
        console.log('initializeCompetitionFilters function called');
        const filterButtons = document.querySelectorAll('.competition-filters .filter-btn');
        const competitionCards = document.querySelectorAll('.competition-card');
        
        console.log('Filter buttons found:', filterButtons.length);
        console.log('Competition cards found:', competitionCards.length);
        console.log('Filter buttons:', filterButtons);
        
        if (filterButtons.length === 0) {
            console.warn('No filter buttons found. Retrying...');
            setTimeout(initializeCompetitionFilters, 200);
            return;
        }
        
        filterButtons.forEach(button => {
            console.log('Adding click listener to button:', button.textContent, 'with data-filter:', button.getAttribute('data-filter'));
            
            button.style.pointerEvents = 'auto';
            button.style.zIndex = '1000';
            
            button.addEventListener('click', function(e) {
                console.log('Button clicked!');
                e.preventDefault();
                e.stopPropagation();
                const filter = this.getAttribute('data-filter');
                console.log('Filter clicked:', filter);
                
                // Update active button
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                
                // Filter competition cards
                competitionCards.forEach(card => {
                    const status = card.getAttribute('data-status');
                    console.log('Card status:', status, 'Filter:', filter);
                    
                    if (filter === 'all' || status === filter) {
                        card.style.display = 'block';
                        card.style.animation = 'cardFadeIn 0.6s ease-out';
                    } else {
                        card.style.display = 'none';
                    }
                });
            });
            
            // Also add a mousedown event to test
            button.addEventListener('mousedown', function(e) {
                console.log('Button mousedown:', this.textContent);
            });
        });
        
        // Add click handlers for competition cards
        competitionCards.forEach(card => {
            card.addEventListener('click', function(e) {
                // Don't trigger if clicking on buttons or interactive elements
                if (e.target.closest('.competition-btn') || e.target.closest('.filter-btn')) {
                    return;
                }
                
                // Add click effect
                this.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
                
                console.log('Competition card clicked:', this.querySelector('.competition-title').textContent);
            });
        });
        
        // Add hover effects for competition stats
        const statCards = document.querySelectorAll('.stat-card');
        statCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px) scale(1.02)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });
    }
    
    // Update competition countdown timers
    function updateCompetitionCountdowns() {
        const countdownTimers = document.querySelectorAll('.countdown-timer');
        
        countdownTimers.forEach(timer => {
            const segments = timer.querySelectorAll('.countdown-segment');
            let totalSeconds = 0;
            
            // Calculate total seconds from current display
            segments.forEach(segment => {
                const value = parseInt(segment.querySelector('.countdown-value').textContent);
                const label = segment.querySelector('.countdown-label').textContent.toLowerCase();
                
                if (label.includes('day')) {
                    totalSeconds += value * 24 * 60 * 60;
                } else if (label.includes('hour')) {
                    totalSeconds += value * 60 * 60;
                } else if (label.includes('minute')) {
                    totalSeconds += value * 60;
                }
            });
            
            // Update countdown
            if (totalSeconds > 0) {
                totalSeconds--;
                
                const days = Math.floor(totalSeconds / (24 * 60 * 60));
                const hours = Math.floor((totalSeconds % (24 * 60 * 60)) / (60 * 60));
                const minutes = Math.floor((totalSeconds % (60 * 60)) / 60);
                const seconds = totalSeconds % 60;
                
                // Update display
                segments.forEach((segment, index) => {
                    const valueElement = segment.querySelector('.countdown-value');
                    const labelElement = segment.querySelector('.countdown-label');
                    
                    if (index === 0) {
                        valueElement.textContent = days;
                        labelElement.textContent = days === 1 ? 'Day' : 'Days';
                    } else if (index === 1) {
                        valueElement.textContent = hours;
                        labelElement.textContent = hours === 1 ? 'Hour' : 'Hours';
                    } else if (index === 2) {
                        valueElement.textContent = minutes;
                        labelElement.textContent = minutes === 1 ? 'Minute' : 'Minutes';
                    }
                });
                
                // Add urgent styling if less than 1 hour
                if (totalSeconds < 3600) {
                    timer.classList.add('urgent');
                }
            }
        });
    }
    
    // Update countdown timers every second
    setInterval(updateCompetitionCountdowns, 1000);
    
    function updateUserInfo(data) {
        const sidebarAvatar = document.querySelector('.sidebar-avatar');
        if (sidebarAvatar && data.profile_picture_url) {
            sidebarAvatar.src = data.profile_picture_url;
        }
        
        // Update avatar in top nav
        const navAvatar = document.querySelector('.profile-avatar');
        if (navAvatar && data.profile_picture_url) {
            navAvatar.src = data.profile_picture_url;
        }
        
        // Update username in sidebar
        const sidebarUsername = document.querySelector('.sidebar-profile-info h4');
        if (sidebarUsername && data.username) {
            sidebarUsername.textContent = data.username;
        }
        
        // Update username in top nav
        const navUsername = document.querySelector('.username');
        if (navUsername && data.username) {
            navUsername.textContent = data.username;
        }
    }
    
});