const buttons = document.querySelectorAll('.copy-btn');

buttons.forEach(button => {
    button.addEventListener('click', () => {
        const numbers = button.getAttribute('data-numbers');
        const labelCopy = button.dataset.copyLabel || '一键复制';
        const labelCopied = button.dataset.copiedLabel || '已复制';
        if (navigator.clipboard) {
            navigator.clipboard.writeText(numbers).then(() => {
                button.textContent = labelCopied;
                setTimeout(() => {
                    button.textContent = labelCopy;
                }, 1500);
            });
        }
    });
});
