class ContactManager {
    constructor() {
        this.form = document.getElementById('contactForm');
        this.init();
    }

    init() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));
            this.addRealTimeValidation();
        }
        this.initializeContactMethods();
        this.initializeFormValidation();
    }

    handleFormSubmit(e) {
        e.preventDefault();
        const formData = new FormData(this.form);

        if (!this.validateForm()) {
            window.toastManager.warning('Validation Error', 'Please fix the errors above.');
            return;
        }

        const submitButton = this.form.querySelector('button[type="submit"]');
        LegalUtils.setButtonLoading(submitButton, true);

        fetch('/contact-submit/', {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.toastManager.success('Success', data.message || 'Thank you! Your message has been sent.');
                this.form.reset();
                this.resetFormValidation();
            } else {
                window.toastManager.error('Error', data.message || 'Sorry, there was an error sending your message.');
            }
        })
        .catch(() => {
            window.toastManager.error('Error', 'Sorry, there was an error sending your message. Please try again.');
        })
        .finally(() => {
            LegalUtils.setButtonLoading(submitButton, false);
        });
    }

    initializeContactMethods() {
        document.querySelectorAll('.contact-method').forEach(method => {
            method.addEventListener('click', (e) => {
                const methodType = e.currentTarget.getAttribute('data-method');
                this.highlightContactMethod(methodType);
            });
        });
    }

    highlightContactMethod(methodType) {
        document.querySelectorAll('.contact-method').forEach(method => method.classList.remove('active'));
        const selectedMethod = document.querySelector(`[data-method="${methodType}"]`);
        if (selectedMethod) selectedMethod.classList.add('active');
    }

    initializeFormValidation() {
        if (this.form) {
            this.form.querySelectorAll('input, select, textarea').forEach(input => {
                input.addEventListener('blur', (e) => this.validateField(e.target));
            });
        }
    }

    addRealTimeValidation() {
        this.form.querySelectorAll('input, select, textarea').forEach(input => {
            input.addEventListener('input', (e) => this.clearFieldError(e.target));
        });
    }

    validateForm() {
        let isValid = true;
        this.form.querySelectorAll('[required]').forEach(field => {
            if (!this.validateField(field)) isValid = false;
        });
        return isValid;
    }

    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';

        this.clearFieldError(field);

        if (field.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = 'This field is required';
        }

        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = 'Please enter a valid email address';
            }
        }

        if (!isValid) this.showFieldError(field, errorMessage);
        return isValid;
    }

    showFieldError(field, message) {
        field.classList.add('is-invalid');
        let errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback';
            field.parentNode.appendChild(errorElement);
        }
        errorElement.textContent = message;
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (errorElement) errorElement.remove();
    }

    resetFormValidation() {
        this.form.querySelectorAll('input, select, textarea').forEach(input => {
            this.clearFieldError(input);
            input.classList.remove('is-valid', 'is-invalid');
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new ContactManager());