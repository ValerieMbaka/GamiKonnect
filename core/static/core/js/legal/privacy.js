document.addEventListener('DOMContentLoaded', function() {
    initializePrivacyPolicy();
});

function initializePrivacyPolicy() {
    animatePrivacyFeatures();
    initializeDataFlow();
    initializeRightsExercise();
}

function animatePrivacyFeatures() {
    const features = document.querySelectorAll('.privacy-feature-card');
    
    features.forEach((feature, index) => {
        setTimeout(() => {
            feature.classList.add('animate__animated', 'animate__fadeInUp');
        }, index * 200);
    });
}

function initializeDataFlow() {
    const dataFlowItems = document.querySelectorAll('.data-flow-item');
    
    dataFlowItems.forEach((item, index) => {
        setTimeout(() => {
            item.classList.add('animate__animated', 'animate__bounceIn');
        }, index * 300);
    });
}

function initializeRightsExercise() {
    const rightButtons = document.querySelectorAll('.exercise-right-btn');
    
    rightButtons.forEach(button => {
        button.addEventListener('click', function() {
            const right = this.getAttribute('data-right');
            simulateRightExercise(right);
        });
    });
}

function simulateRightExercise(right) {
    const messages = {
        'access': 'We are preparing your data access report...',
        'rectification': 'Please provide the corrected information...',
        'erasure': 'Initiating data deletion process...',
        'restriction': 'Applying usage restrictions to your data...',
        'portability': 'Compiling your data for portability...',
        'objection': 'Processing your objection request...'
    };
    
    const message = messages[right] || 'Processing your request...';
    showToast(message, 'info');
    
    setTimeout(() => {
        showToast(`Your ${right} request has been processed successfully!`, 'success');
    }, 1500);
}

function exportMyData() {
    showToast('Preparing your data export...', 'info');
    
    setTimeout(() => {
        showToast('Your data export is ready for download!', 'success');
    }, 2500);
}