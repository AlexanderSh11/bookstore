async function addToCart(bookId, userId) {
    console.log('Функция вызвана с:', bookId, userId);
    try {
        const response = await fetch('http://localhost:5001/cart/add', {
            method: 'POST',
            mode: 'cors',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                book_id: bookId,
                user_id: userId
            })
        });
        
        if (response.ok) {
            alert('Товар добавлен!');
        } else {
            alert('Ошибка: ' + await response.text());
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
}