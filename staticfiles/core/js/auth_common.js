class BaseAuthManager {
    constructor() {}

    toggleButtonState(btn, disabled, text = null) {
        if (!btn) return;
        btn.disabled = disabled;
        if (text) {
            btn.textContent = text;
        }
    }

    async sendFormRequest(formElement) {
        const formData = new FormData(formElement);
        
        try {
            const response = await fetch(formElement.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Request failed:', error);
            throw new Error('Network error or invalid server response.');
        }
    }
}
