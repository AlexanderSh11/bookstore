async function checkout() {
    const data = {
        payment_method: document.getElementById('payment_method').value,
        shipping_address: document.getElementById('shipping_address').value
    };
    
    try {
        const response = await fetch('http://localhost:5002/checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Ошибка сервера');
        }
        
        const result = await response.json();
        console.log('Успех:', result);
        alert('Заказ успешно оформлен! Номер заказа: ' + result.order_id);
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка при оформлении заказа: ' + error.message);
    }
}