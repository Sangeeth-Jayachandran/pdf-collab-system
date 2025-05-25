// Handle file upload display
document.addEventListener('DOMContentLoaded', function() {
    // Update file name display when a file is selected
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const fileName = this.files[0] ? this.files[0].name : 'No file selected';
            const label = this.nextElementSibling;
            label.textContent = fileName;
        });
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Copy share link to clipboard
    const copyButtons = document.querySelectorAll('.copy-share-link');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const link = this.dataset.link;
            navigator.clipboard.writeText(link).then(() => {
                const tooltip = bootstrap.Tooltip.getInstance(this);
                this.setAttribute('data-bs-original-title', 'Copied!');
                tooltip.show();
                
                setTimeout(() => {
                    this.setAttribute('data-bs-original-title', 'Copy to clipboard');
                    tooltip.hide();
                }, 2000);
            });
        });
    });
});