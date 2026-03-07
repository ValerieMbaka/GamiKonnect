document.addEventListener('DOMContentLoaded',()=>{
    const searchInput=document.getElementById('gamesSearch');
    const platformFilter=document.getElementById('platformFilter');
    const genreFilter=document.getElementById('genreFilter');
    const gamesGrid=document.getElementById('gamesGrid');
    const emptyState=document.getElementById('gamesEmptyState');
    const clearFiltersBtn=document.getElementById('clearFiltersBtn');
    const refreshBtn=document.getElementById('refreshGamesBtn');

    if(!gamesGrid) return;

    const cards=Array.from(gamesGrid.querySelectorAll('.game-card'));

    function applyFilters(){
        const query=(searchInput?.value||'').toLowerCase().trim();
        const platformValue=platformFilter?.value||'all';
        const genreValue=genreFilter?.value||'all';
        let visibleCount=0;

        cards.forEach(card=>{
            const name=(card.dataset.name||'').toLowerCase();
            const platforms=(card.dataset.platforms||'').split(' ').filter(Boolean);
            const genres=(card.dataset.genres||'').split(' ').filter(Boolean);

            const matchesSearch=!query||name.includes(query);
            const matchesPlatform=platformValue==='all'||platforms.includes(platformValue);
            const matchesGenre=genreValue==='all'||genres.includes(genreValue);

            const shouldShow=matchesSearch&&matchesPlatform&&matchesGenre;
            card.style.display=shouldShow?'flex':'none';
            if(shouldShow) visibleCount++;
        });

        if(emptyState){
            emptyState.style.display=visibleCount?'none':'flex';
        }
    }

    if(searchInput){
        searchInput.addEventListener('input',()=>{
            window.clearTimeout(searchInput._debounce);
            searchInput._debounce=setTimeout(applyFilters,160);
        });
    }
    platformFilter?.addEventListener('change',applyFilters);
    genreFilter?.addEventListener('change',applyFilters);

    clearFiltersBtn?.addEventListener('click',()=>{
        if(searchInput) searchInput.value='';
        if(platformFilter) platformFilter.value='all';
        if(genreFilter) genreFilter.value='all';
        applyFilters();
    });

    refreshBtn?.addEventListener('click',()=>{
        applyFilters();
        window.scrollTo({top:0,behavior:'smooth'});
    });

    applyFilters();
});
