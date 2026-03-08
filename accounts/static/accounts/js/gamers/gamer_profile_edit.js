// Gamer Profile Edit – mirrored game search & selection UX (with original form features)
document.addEventListener('DOMContentLoaded', function() {
    // Style injection (idempotent)
    if(!document.getElementById('gp-edit-enhance-styles')){
        const s=document.createElement('style');
        s.id='gp-edit-enhance-styles';
        s.textContent=`
            .chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
            .chip{background:#f1f5f9;color:#334155;padding:4px 10px;border-radius:16px;font-size:12px;cursor:pointer;user-select:none;display:inline-flex;align-items:center;gap:6px;position:relative;transition:background .15s ease,color .15s ease,box-shadow .25s ease}
            .chip.active{background:#2563eb;color:#fff}
            .chip.pending{background:#fff7ed;color:#b45309;border:1px solid #fbbf24}
            .chip .remove{font-weight:bold;cursor:pointer;margin-left:4px}
            .chip.chip-just-added{box-shadow:0 0 0 3px rgba(37,99,235,.35);animation:fadeGlow .7s forwards}
            @keyframes fadeGlow{0%{box-shadow:0 0 0 3px rgba(37,99,235,.35)}100%{box-shadow:none}}
            .game-suggestions{max-height:220px;overflow-y:auto;border:1px solid #d0d7de;border-radius:6px;background:#fff;margin-top:4px;box-shadow:0 4px 12px rgba(0,0,0,.08)}
            .game-suggestions .suggestion-item{padding:8px 10px;cursor:pointer;font-size:14px;line-height:18px}
            .game-suggestions .suggestion-item:hover{background:#f0f7ff}
            .game-suggestions .suggestion-item.active{background:#2563eb;color:#fff}
        `;
        document.head.appendChild(s);
    }

    const form = document.getElementById('editProfileForm');
    const about = document.getElementById('id_about');
    const aboutCounter = document.getElementById('aboutCounter');
    const updateAboutCounter = ()=>{ if(aboutCounter) aboutCounter.textContent=`${(about.value||'').length}/200`; };
    if(about){ about.addEventListener('input', updateAboutCounter); updateAboutCounter(); }

    // Username generator & availability
    const usernameInput = document.getElementById('id_custom_username');
    const usernameError = document.getElementById('custom_username-error');
    const generateBtn = document.getElementById('generateUsernameBtn');
    const usernamePattern=/^[A-Za-z0-9_]{3,15}$/;
    const originalUsername = usernameInput ? (usernameInput.getAttribute('data-original-username') || usernameInput.value || '').trim() : '';
    const adjectives=['Swift','Nova','Crimson','Shadow','Aero','Frost','Blaze','Quantum','Pixel','Hyper','Omega','Ultra'];
    const nouns=['Ranger','Ninja','Falcon','Viper','Phoenix','Comet','Drifter','Guardian','Samurai','Spectre','Voyager','Gamer'];
    function genCandidate(){
        const a=adjectives[Math.floor(Math.random()*adjectives.length)];
        const n=nouns[Math.floor(Math.random()*nouns.length)];
        const num=Math.floor(Math.random()*9999).toString().padStart(2,'0');
        let c=`${a}${n}${num}`;
        if(c.length>15)c=c.slice(0,15);
        return c;
    }
    async function checkAvailability(){
        if(!usernameInput) return false;
        const v=(usernameInput.value||'').trim();
        if(!usernamePattern.test(v)){
            if(usernameError) usernameError.textContent='Use 3–20 letters, numbers, or underscores';
            return false;
        }
        // If username hasn't changed from the original, treat as available
        if(originalUsername && v.toLowerCase()===originalUsername.toLowerCase()){
            if(usernameError) usernameError.textContent='';
            return true;
        }
        if(window.usernameRateLimitedUntil && Date.now()<window.usernameRateLimitedUntil) return false;
        try{
            const res=await fetch('/accounts/check-username/?username='+encodeURIComponent(v));
            const data=await res.json();
            if(data.reason==='rate_limited'){
                const retry=(data.retry_after||30)*1000;
                window.usernameRateLimitedUntil=Date.now()+retry;
                if(typeof showToast==='function') showToast('Too many username checks. Wait '+data.retry_after+'s.','warning');
                return false;
            }
            if(!data.available){
                if(usernameError) usernameError.textContent= data.reason==='invalid_format'?'Invalid username format':'This username is already taken';
                return false;
            }
            if(usernameError) usernameError.textContent='';
            return true;
        }catch(e){
            console.error(e);
            return false;
        }
    }
    let uTimer; function debouncedUserCheck(){ clearTimeout(uTimer); uTimer=setTimeout(checkAvailability,400);} if(usernameInput){ usernameInput.addEventListener('input',debouncedUserCheck); usernameInput.addEventListener('blur',checkAvailability);} if(generateBtn){ generateBtn.addEventListener('click', async()=>{ generateBtn.disabled=true; const original=generateBtn.innerHTML; generateBtn.innerHTML='<i class="fas fa-dice"></i> Generating...'; let final=null; for(let i=0;i<10;i++){ const cand=genCandidate(); usernameInput.value=cand; // eslint-disable-next-line no-await-in-loop
            const ok=await checkAvailability(); if(ok){ final=cand; break;} } if(!final){ if(typeof showToast==='function') showToast('Could not generate a unique username, try manually.','error'); } generateBtn.disabled=false; generateBtn.innerHTML=original; }); }

    // Dynamic platform categories (mirrors completion logic)
    const platformsContainerEdit = document.getElementById('platformsTagsEdit');
    let platformHidden = document.getElementById('id_platforms');
    let allPlatforms = []; // unified list of selectable names
    let selectedPlatforms = [];
    let originalPlatformsLower = new Map(); // lowercased -> original casing

    function safeParsePlatforms(raw) {
        if (!raw || typeof raw !== 'string') return [];
        // Trim whitespace
        const str = raw.trim();
        // Quick fast-path: valid JSON array with double quotes
        if (/^\[\s*"/.test(str) || str === '[]') {
            try { const j = JSON.parse(str); return Array.isArray(j) ? j : []; } catch { return []; }
        }
        // Handle Python-style list repr with single quotes: ['PlayStation','Xbox']
        if (/^\[\s*'/.test(str)) {
            try {
                const converted = str
                    .replace(/'/g, '"');
                const j = JSON.parse(converted);
                return Array.isArray(j) ? j : [];
            } catch { /* fall through */ }
        }
        // Fallback: attempt to wrap items if comma-separated
        if (!str.startsWith('[') && str.includes(',')) {
            const arr = str.split(',').map(s => s.trim()).filter(Boolean);
            return arr;
        }
        // Single value fallback
        if (!str.startsWith('[') && str.length) return [str];
        return [];
    }

    // Initial selection from hidden field or data attribute
    if (platformHidden && platformHidden.value) {
        const parsed = safeParsePlatforms(platformHidden.value);
        selectedPlatforms = parsed;
        parsed.forEach(name => {
            const key = (name || '').toString().toLowerCase();
            if (key && !originalPlatformsLower.has(key)) {
                originalPlatformsLower.set(key, name);
            }
        });
    }
    if ((!selectedPlatforms || selectedPlatforms.length === 0) && platformsContainerEdit && platformsContainerEdit.dataset.existingPlatforms) {
        const parsedExisting = safeParsePlatforms(platformsContainerEdit.dataset.existingPlatforms);
        selectedPlatforms = parsedExisting;
        parsedExisting.forEach(name => {
            const key = (name || '').toString().toLowerCase();
            if (key && !originalPlatformsLower.has(key)) {
                originalPlatformsLower.set(key, name);
            }
        });
    }

    async function fetchPlatformCategories() {
        try {
            const data = await safeFetchJson('/games/get-profile-form-data/');
            if (!data.success) return;
            const categories = Array.isArray(data.platform_categories) ? data.platform_categories : [];
            const built = [];
            categories.forEach(c => {
                const cname = (c.name || '').toLowerCase();
                if (cname === 'console' || cname === 'consoles') {
                    built.push({ id: 'console_ps', name: 'PlayStation' });
                    built.push({ id: 'console_xbox', name: 'Xbox' });
                    built.push({ id: 'console_switch', name: 'Nintendo Switch' });
                } else {
                    // Preserve original casing of stored platforms when building display names
                    built.push({ id: `cat_${c.id}`, name: c.name });
                }
            });
            // Fallback if categories missing: attempt platforms list presence
            if (!built.length && Array.isArray(data.platforms)) {
                built.push(...data.platforms.map(p => ({ id: p.id, name: p.name })));
            }
            allPlatforms = built;
            renderPlatformsEdit();
        } catch (e) { console.warn('Platform categories load failed', e); }
    }

    function renderPlatformsEdit() {
        if (!platformsContainerEdit) return;
        platformsContainerEdit.innerHTML = '';
        allPlatforms.forEach(p => {
            const chip = document.createElement('span');
            const key = (p.name || '').toString().toLowerCase();
            const active = selectedPlatforms.some(sp => sp.toLowerCase() === key);
            chip.className = 'chip' + (active ? ' active' : '');
            // Use original casing if we have it, otherwise fall back to category name
            chip.textContent = originalPlatformsLower.get(key) || p.name;
            chip.dataset.id = p.id;
            chip.addEventListener('click', () => {
                const already = selectedPlatforms.find(sp => sp.toLowerCase() === key);
                if (already) {
                    selectedPlatforms = selectedPlatforms.filter(sp => sp.toLowerCase() !== key);
                } else {
                    // When adding new, store in category casing but also track for future
                    selectedPlatforms.push(p.name);
                    const addKey = (p.name || '').toString().toLowerCase();
                    if (addKey && !originalPlatformsLower.has(addKey)) {
                        originalPlatformsLower.set(addKey, p.name);
                    }
                }
                syncPlatformsHidden();
                renderPlatformsEdit();
                validatePlatformsEdit();
            });
            platformsContainerEdit.appendChild(chip);
        });
        syncPlatformsHidden();
    }

    function syncPlatformsHidden() {
        if (platformHidden) {
            platformHidden.value = JSON.stringify(selectedPlatforms);
        }
    }

    function validatePlatformsEdit() {
        const err = document.getElementById('platforms-error');
        if (!err) return;
        if (selectedPlatforms.length === 0) {
            err.textContent = 'Select at least one platform';
            err.classList.add('show');
        } else {
            err.textContent = '';
            err.classList.remove('show');
        }
    }

    fetchPlatformCategories();
    validatePlatformsEdit();

    // Game selection mirrored UX
    const input=document.getElementById('games_input');
    const suggestionsBox=document.getElementById('gameSuggestionsEdit');
    const chipsContainer=document.getElementById('selectedGames');
    const hiddenField=document.getElementById('id_games');
    const gamesError=document.getElementById('games-error');
    let defaultGames=[]; // {id,name}
    let selectedGames=[]; // names
    let suggestionData=[]; let activeIndex=-1; let pendingCustom=new Set();
    // Init selected from hidden (comma list)
    const initial=(hiddenField?.value||'').trim(); if(initial){ selectedGames=initial.split(',').map(v=>v.trim()).filter(Boolean); }
    function validateGames(){ if(!gamesError) return; if(selectedGames.length===0){ gamesError.textContent='Games is required'; gamesError.classList.add('show'); } else { gamesError.textContent=''; gamesError.classList.remove('show'); } }
    function syncHidden(){ if(hiddenField) hiddenField.value=selectedGames.join(','); }
    function renderChips(){ if(!chipsContainer) return; chipsContainer.innerHTML=''; selectedGames.forEach(name=>{ const chip=document.createElement('span'); chip.className='chip active'+(pendingCustom.has(name.toLowerCase())?' pending':'')+' chip-just-added'; chip.textContent=name; const rm=document.createElement('span'); rm.className='remove'; rm.dataset.game=name; rm.textContent='×'; rm.addEventListener('click',e=>{ e.stopPropagation(); removeGame(name); }); chip.appendChild(rm); chipsContainer.appendChild(chip); setTimeout(()=> chip.classList.remove('chip-just-added'),750); }); syncHidden(); validateGames(); }
    function addGame(raw){ const name=(raw||'').trim(); if(!name) return; const lower=name.toLowerCase(); if(selectedGames.some(n=> n.toLowerCase()===lower)) return; const match=defaultGames.find(g=> g.name.toLowerCase()===lower); if(match){ selectedGames.push(match.name); } else { selectedGames.push(name); pendingCustom.add(lower); } renderChips(); }
    function removeGame(name){ const lower=name.toLowerCase(); selectedGames=selectedGames.filter(n=> n.toLowerCase()!==lower); pendingCustom.delete(lower); renderChips(); }
    async function safeFetchJson(url){ const res=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest'}}); const text=await res.text(); if(text.trim().startsWith('<')) return {success:false,html:true}; try{return JSON.parse(text);}catch{return {success:false,parse_error:true};} }
    async function loadDefaults(){ try{ const data=await safeFetchJson('/games/get-profile-form-data/'); if(data.success) defaultGames=Array.isArray(data.games)?data.games:[]; }catch(e){ console.warn('Defaults load failed',e);} }
    function buildSuggestions(query){ const term=(query||'').toLowerCase(); suggestionsBox.innerHTML=''; if(!term){ suggestionsBox.style.display='none'; return;} suggestionData=defaultGames.filter(g=> g.name.toLowerCase().includes(term)).slice(0,8); if(!suggestionData.length){ suggestionsBox.style.display='none'; return;} suggestionData.forEach((g,i)=>{ const div=document.createElement('div'); div.className='suggestion-item'; div.textContent=g.name; div.dataset.index=i; div.addEventListener('mouseenter',()=>{ activeIndex=i; setActive(false); }); div.addEventListener('mousedown',e=>{ e.preventDefault(); addGame(g.name); input.value=''; hideSuggestionsSoon(); }); suggestionsBox.appendChild(div); }); suggestionsBox.style.display='block'; activeIndex=-1; setActive(false); }
    function setActive(autoScroll){ const items=[...suggestionsBox.children]; items.forEach((el,i)=>{ if(i===activeIndex){ el.classList.add('active'); if(autoScroll) el.scrollIntoView({block:'nearest'}); } else el.classList.remove('active'); }); }
    function hideSuggestionsSoon(){ setTimeout(()=>{ suggestionsBox.style.display='none'; },400); }
    if(input){ input.addEventListener('input',()=> buildSuggestions(input.value)); input.addEventListener('keydown',e=>{ const hidden=!suggestionsBox || suggestionsBox.style.display==='none'; if(hidden){ if(e.key==='Enter'){ e.preventDefault(); const val=input.value.trim(); if(val) addGame(val); input.value=''; return;} if(e.key==='ArrowDown'){ buildSuggestions(input.value); return;} } if(e.key==='ArrowDown'){ e.preventDefault(); if(suggestionData.length){ activeIndex=(activeIndex+1)%suggestionData.length; setActive(true); } } else if(e.key==='ArrowUp'){ e.preventDefault(); if(suggestionData.length){ activeIndex=(activeIndex-1+suggestionData.length)%suggestionData.length; setActive(true); } } else if(e.key==='Enter'){ e.preventDefault(); if(activeIndex>=0 && suggestionData[activeIndex]){ addGame(suggestionData[activeIndex].name); } else if(suggestionData.length){ addGame(suggestionData[0].name); } else { const val=input.value.trim(); if(val) addGame(val); } input.value=''; suggestionsBox.style.display='none'; } else if(e.key==='Escape'){ suggestionsBox.style.display='none'; } }); input.addEventListener('blur',()=> setTimeout(()=>{ suggestionsBox.style.display='none'; },150)); }
    chipsContainer?.addEventListener('click',e=>{ if(e.target.classList.contains('remove-game')){ const nm=e.target.dataset.game; if(nm) removeGame(nm); } });
    renderChips(); loadDefaults();

    // Avatar preview
    const profilePicInput=document.getElementById('id_profile_picture'); const currentProfilePic=document.getElementById('currentProfilePic'); if(profilePicInput && currentProfilePic){ profilePicInput.addEventListener('change',e=>{ const f=e.target.files[0]; if(f){ if(!f.type.startsWith('image/')){ if(typeof showToast==='function') showToast('Please select an image file.','error'); return;} if(f.size>5*1024*1024){ if(typeof showToast==='function') showToast('File must be <5MB','error'); return;} const reader=new FileReader(); reader.onload=ev=>{ currentProfilePic.src=ev.target.result; }; reader.readAsDataURL(f); } }); }

    // Form submission override (use FormData; handle games/platforms similarly)
    if(form){ form.addEventListener('submit', async e=>{ e.preventDefault(); let ok=true; ok=(await checkAvailability()) && ok; const bio=document.getElementById('id_bio'); if(bio){ const bVal=bio.value.trim(); if(bVal.length<5 || bVal.length>30){ const bioError=document.getElementById('bio-error'); if(bioError){ bioError.textContent='Bio must be 5–30 characters'; bioError.classList.add('show'); } ok=false; } else { const bioError=document.getElementById('bio-error'); if(bioError){ bioError.textContent=''; bioError.classList.remove('show'); } } }
        const aboutField=document.getElementById('id_about'); if(aboutField){ const len=aboutField.value.trim().length; if(len && (len<5 || len>200)){ if(typeof showToast==='function') showToast('About must be 5–200 characters if provided','error'); ok=false; } }
        const location=document.getElementById('id_location'); if(location && !location.value.trim()){ const locationError=document.getElementById('location-error'); if(locationError) locationError.textContent='Location is required'; ok=false; }
        if(selectedPlatforms.length===0) ok=false; if(selectedGames.length===0) ok=false; validatePlatformsEdit(); validateGames(); if(!ok){ if(typeof showToast==='function') showToast('Please fix the highlighted fields before saving.','error'); return; } const submitBtn=form.querySelector('button[type="submit"]'); const originalHTML=submitBtn.innerHTML; submitBtn.innerHTML='<i class="fas fa-spinner fa-spin"></i> Saving...'; submitBtn.disabled=true; const fd=new FormData(form); fd.set('platforms', platformHidden.value); fd.set('games', selectedGames.join(',')); try{ const csrf=document.querySelector('[name=csrfmiddlewaretoken]')?.value||''; if(typeof showToast==='function') showToast('Saving profile changes...','info'); const resp=await fetch(form.dataset.url||window.location.href,{ method:'POST', body:fd, headers:{'X-CSRFToken':csrf,'X-Requested-With':'XMLHttpRequest'} }); if(resp.ok){ let data=null; try{ data=await resp.json(); }catch(parseErr){ console.error('Parse error',parseErr); } if(data && data.success){ if(typeof showToast==='function') showToast(data.message||'Profile updated successfully!','success'); if(data.user) localStorage.setItem('userProfileData', JSON.stringify(data.user)); if(data.user_stats) localStorage.setItem('userStats', JSON.stringify(data.user_stats)); updateProfilePictures(data.user); setTimeout(()=>{ window.location.href='/accounts/gamer-settings/'; },1200); } else { if(typeof showToast==='function') showToast((data&&data.message)||'Failed to update profile.','error'); } } else { if(typeof showToast==='function') showToast('Network error saving profile.','error'); } }catch(err){ console.error(err); if(typeof showToast==='function') showToast('Unexpected error.','error'); } submitBtn.innerHTML=originalHTML; submitBtn.disabled=false; }); }
});

function updateProfilePictures(userData){ if(!userData || !userData.profile_picture_url) return; const headerProfilePic=document.querySelector('.profile-avatar, .profile-btn img'); if(headerProfilePic) headerProfilePic.src=userData.profile_picture_url; const sidebarProfilePic=document.querySelector('.sidebar-profile img, .nav-profile img'); if(sidebarProfilePic) sidebarProfilePic.src=userData.profile_picture_url; const all=document.querySelectorAll('img[src*="profile_pics"], img[src*="player.jpeg"]'); all.forEach(img=>{ img.src=userData.profile_picture_url; }); if(userData.custom_username){ document.querySelectorAll('.username, .nav-username').forEach(el=> el.textContent=userData.custom_username); } }

