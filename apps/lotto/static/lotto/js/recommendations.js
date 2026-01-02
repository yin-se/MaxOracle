const buttons = document.querySelectorAll('.copy-btn');

buttons.forEach(button => {
    button.addEventListener('click', () => {
        const numbers = button.getAttribute('data-numbers');
        if (navigator.clipboard) {
            navigator.clipboard.writeText(numbers).then(() => {
                button.textContent = '已复制';
                setTimeout(() => {
                    button.textContent = '一键复制';
                }, 1500);
            });
        }
    });
});
